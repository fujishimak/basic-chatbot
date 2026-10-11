from asyncio.log import logger
import time
from datetime import datetime
from sqlalchemy.sql.operators import is_boolean
from langchain.messages import ToolMessage
from reflex_components_core.el import Base
from asyncio import timeout
from typing import Optional, Literal
from langchain.tools import tool
import reflex as rx
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate, MessagesPlaceholder, ChatPromptTemplate
from langchain_classic.output_parsers import BooleanOutputParser, PydanticOutputParser
from langchain_classic.output_parsers import DatetimeOutputParser
from openai import APIError
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pprint import pformat
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__) # returns the root logger to which we will have attached our Logging Handler for openlit

# Helper function to extract text from returned AIMessage payloads which could be string or list/dict
def content_to_text(content) -> str:
    # If it's string just return it
    if isinstance(content,str):
        logger.info("Payload confirmed as string | content=%r", content) # Do not use f-strings so we can take advantage of lazy formatting
        return content
    elif isinstance(content,list):
        logger.info("Payload is non-string")
        # Assume list in which case we need to stich the text parts together. We will not handle images right now.
        parts = []
        for block in content:
            if isinstance(block, str):
                logger.debug("Content block is string | block=%r", block)
                parts.append(block)
            elif isinstance(block, dict):
                logger.debug("Content block contains a dict | dict=%s", pformat(block))
                parts.append(block.get("text", ""))
                # We will skip images, tools or other blocks

        logger.info("Returning textual content")
        logger.debug("Text part list contains: %s", [c for c in parts])
        return "".join(parts)
    else:
        raise Exception("Unknown content type")

######## SEARCH TOOL START ########

# Specify the Pydantic model for structured input for search
# Field itself is a function, not a class, used to add metadata and configuration that your type annotation cannot express
class SearchInput(BaseModel):
    """ Accept input for searching """
    query: str = Field(description="The user's query")
    max_results: int = Field(default=5, description="Maximum number of results to return", )

class SearchResult(BaseModel):
    """ A single search result """
    id: str
    title: str
    url: str
    content: str
    score: float | None = None
    published_date: str | None = None

class SearchResults(BaseModel):
    """ The full structured search response. """
    query: str
    answer: str | None = None
    # Safest way to create an empty list...if we just used [] it would be shared across all instances
    results: list[SearchResult] = Field(default_factory=list)

# The tool decorator wraps the output of this as a ToolMessage
# args_schema allows us to do input validation
@tool(args_schema=SearchInput) 
async def search_tool(query: str, max_results: int = 5) -> dict:
    """
    Search the web for real-time information, news, current events, and facts.
    Use this tool whenever the user asks a question requiring outside knowledge.
    """
    # Make the call to the Tavily API. We do this async because we do not want to freeze the event loop while awaiting the call via client.post
  
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            headers={
                "Content-Type":"application/json",
                "X-Tavily-Access-Mode":"keyless"
            },
            json={
                "query": query, 
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": True}
        )
    # Launch search and pass back max_results 
        response.raise_for_status()
    
    data = response.json()
    parsed = SearchResults(
        query=query,
        answer=data.get("answer"),
        results=data.get("results", [])
    ) # Automatically coerces data into the shape we created

    # Result is fed back as a serialisable payload (str, dict)
    return parsed.model_dump()

######## SEARCH TOOL END ########

######## TOPIC CLASSIFIER TOOL START ########

class TopicClassifierInput(BaseModel):
    """ Accept input for searching """
    query: str = Field(description="The user's query")
    preferred_topic: str = Field(default="Python", description="The preferred topic of conversation")

class TopicClassifierOutput(BaseModel):
    """ Return a boolean representing whether or not the query is off-topic """
    approved: bool

@tool(args_schema=TopicClassifierInput)
async def approve_query_topic(query: str, preferred_topic: str = "Python"):
    """
    Assess the user's query to verify if on-topic or not. 
    """
    classifier_template = ChatPromptTemplate.from_messages([
            ("system","You are a fast classifier of topics given a user's query. Verify if the user's input query matches {preferred_topic}, and return YES or NO only."),
            ("human", "{user_input}")
        ])

    classifier_llm = ChatOpenAI(
        base_url=os.environ.get("SPUR_ENDPOINT"),
        api_key=os.environ.get("CLASSIFIER_API_KEY"),
        model="spur-chat-mini",
        temperature=0.0,
    )

    topic = "Python"
    prompt = classifier_template.invoke(
            {
                "user_input":query,
                "preferred_topic": f"{topic}",
                },       
            )

    # Set up our parser
    parser = BooleanOutputParser()

    # Now we perform an async invoke of the parser and llm since this involves a network call
    # We can chain this and have a single awaitable pipeline rather than doing multiple awaits

    chain = classifier_llm | parser
    retries = 0

    response = False
    
    # SLMs will sometimes ignore instructions so look out for a ValueError, we will retry
    while retries < 3:
        try:
            response = await chain.ainvoke(prompt)
            if isinstance(response, bool):
                break
        except Exception as e:
            retries+=1
            response = False # Fail closed
            continue

    # When we exit we expect response to be False at worst
    parsed = TopicClassifierOutput(approved=response)

    return parsed.model_dump()


######## TOPIC CLASSIFIER TOOL END ########

######## DATE TOOL START ########
class ContentCategoryOutput(BaseModel):
    """ Detects whether or not the user's input falls into the category of harmful content """
    contains_hate_speech: bool = Field(description="Indicates if the user's query contains hate speech")
    contains_violence: bool = Field(description="Indicates if the user's query contains violence")
    toxicity_rating: Literal["NONE","LOW","MEDIUM","HIGH"] = Field(description="A four-scale rating of toxicity with NONE, LOW, MEDIUM, HIGH")

@tool
async def detect_toxicity(query: str) -> dict:
    """
    Assess the user's query to verify if it contains hate speech or violence and rate the overall level of toxicity. 
    """

    #Set up parser
    parser = PydanticOutputParser(pydantic_object=ContentCategoryOutput)

    content_template = ChatPromptTemplate.from_messages([
            ("system","You are a fast detector of toxicity given a user's query. Verify if the user's input query contains either or both of hate speech and violence and output True or False to each category accordingly. Include an overall toxicity rating of NONE, LOW, MEDIUM or HIGH in your response. Say nothing else other than what you have been directed."),
            ("human", "{user_input}")
        ])

    content_llm = ChatOpenAI(
        base_url=os.environ.get("SPUR_ENDPOINT"),
        api_key=os.environ.get("CLASSIFIER_API_KEY"),
        model="spur-chat-mini",
        #model="spur-auto",
        temperature=0.0,
    )

    prompt = content_template.invoke(
        {
            "user_input":query,
            #"format_instructions": parser.get_format_instructions()
            },       
        )

    # We use with_structured_output for this one because unlike topic detection  we need robustness to prose.

    structured_llm = content_llm.with_structured_output(ContentCategoryOutput)

    response = await structured_llm.ainvoke(prompt)

    return response

######## DATE TOOL END ########


class State(rx.State):
    # The current question being asked
    question: str = ""

    #Keep track of the chat history as a list of (question,answer) tuples.
    # Technically speaking memory should be part of the harness rather than the state itself.
    chat_history: list[tuple[str,str]] = []
    processing: bool = False
    error: str = ""

    # Now define our question and answer events. This is similar to useEffect scenarios in React
    # Only methods generated by rx.event are allowed to update state
    @rx.event
    def set_question(self,value:str):
        self.question = value

    # Run non-blocking so that we do not freeze the event loop
    @rx.event(background=True)
    async def answer(self):
        
        # Ensure that our prompt template has a slot for historical messages
        prompt_template = ChatPromptTemplate.from_messages([
            ("system","You introduce yourself as a helpful assistant who knows all about {topic}. You provide helpful details and references when asked. You also ask follow-up questions to better understand how to be useful. You use clear professional language, and are as succinct as possible. Before providing a response you always ensure that that the query topic is approved for discussion. if it is not, you politely decline, asking the use to stay on {topic}. Before providing a response you also try to detect toxicity in the user's query. If the toxicity rating is anything other than NONE, you decline to engage. Specifically, if the toxicity rating is HIGH, you tell the user `Please jump offa mi bumpah`, and refuse to engage until they apologise."),
            MessagesPlaceholder("history"),
            ("human", "{user_input}")
        ])
        # We're not allowed to read self.* outside of a lock. Keep this around to store the question for lock-free work.
        question: str = "" 
        history_messages = []

        # Set up tools
        tools = [search_tool, approve_query_topic, detect_toxicity]
        tools_by_name = {t.name : t for t in tools}

        # Snapshotting: acquire a lock and perform any mutations necessary
        async with self:
            if not (os.environ.get("OPENAI_API_KEY")):
                self.error="Set the API key and reload the app"
                return

            llm = ChatOpenAI(
                base_url=os.environ.get("SPUR_ENDPOINT"), #LangChain automatically appends /chat/completions
                model="spur-auto",
                temperature=0.0,
                
            )

            model_with_tools = llm.bind_tools(tools)
            # Grab the current question since we will need this to build the prompt later
            question = self.question

            # Now snapshot the chat's history so we can populate memory. Nested list comprehension...not very readable though...
            history_messages = [
                m
                for past_q, past_a in self.chat_history
                for m in (HumanMessage(past_q), AIMessage(past_a))
            ]

            self.processing = True
            self.error = ""
            self.chat_history.append((question, ""))
            # If we are here then 'Ask' was clicked. Clear the input so the user can type additional items. Will reflect on yield
            self.question = ""
            
        #Yield here to clear frontend before continuing. We return control to the application
        #State updates are batched and pushed to the frontend, which allows the input box to be cleared
        #Yield is fire and forget, the backend continues its work
        yield

        # Build the prompt, we call invoke() to get a resolved string that has our variables filled in.
        # Use local variables so we can run lock-free
        topic = "Python"
        prompt = prompt_template.invoke(
                {
                    "user_input":question,
                    "topic": f"{topic}",
                    "history":history_messages # MessagesPlaceholder slot
                    },
                
                )
        
        ai_msg = await model_with_tools.ainvoke(prompt)
        messages = prompt.to_messages()
        messages.append(ai_msg) # Append the AI's latest message in context. Tool calls usually have tool_calls populated

        if ai_msg.tool_calls:
            
            # Find out what the model asked for, if anything
            for call in ai_msg.tool_calls:
                tool = tools_by_name[call["name"]]
                result = await tool.ainvoke(call["args"])
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))
        # If we have no tool calls then ai_msg is already appended so we will write directly

        # At this point we can now stream the response back 
        async for chunk in model_with_tools.astream(messages):
            try:
                text = content_to_text(chunk.content)
                async with self:
                    self.chat_history[-1] = (self.chat_history[-1][0], self.chat_history[-1][1] + text)
                yield
            except APIError:
                async with self:
                    self.chat_history[-1] = (self.chat_history[-1][0],"The request failed, please try again")
                    self.error = "Request failed"
                yield
            except Exception as e:
                continue # We found something that wasn't str or list, swallow the exception, skip the block and move on
        
        # If we succeeded here then we're done processing...mutate processing state safely
        async with self:
            self.processing = False
        yield rx.set_focus("question_input") #refocus to the input box.

     
        

