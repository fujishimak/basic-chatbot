"""Welcome to Reflex! This file outlines the steps to create a basic app."""
from sqlalchemy import false
from basic_chatbot.logging_config import setup_logging
import openlit


import reflex as rx

from rxconfig import config

from basic_chatbot import style

from basic_chatbot.state import State

setup_logging()
openlit.init() # traces/metrics; reads the same OTEL endpoint env var

def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        chat(),
        action_bar(),
        rx.cond(State.error != "", rx.text(State.error, color="red", role="alert")),
        style=style.index_style,
    )

def qa(question: str, answer: str) -> rx.Component:
    return rx.vstack(
        rx.box(question, text_align="right", style=style.question_style),
        rx.box(answer, text_align="left", style=style.answer_style),
        margin_y="1em",
        width="100%"
        )

def chat() -> rx.Component:
    return rx.box(
        rx.foreach(State.chat_history, lambda messages: qa(messages[0], messages[1]))
    )

def action_bar() -> rx.Component:
    return rx.form(
        rx.hstack(
            rx.input(
                id="question_input", # need this so we can refocus to this input after submission
                value=State.question, # Need this because we will clear from the State object, and if we didn't then the input would never reflect empty after submission
                disabled=State.processing,
                on_change=State.set_question,
                placeholder="Ask a question", 
                style=style.input_style
                ),
            rx.button(
                "Ask", 
                loading=State.processing, 
                style=style.button_style,
                ),
            width="100%"
        ),
        on_submit=State.answer,
        reset_on_submit=False
    )

app = rx.App()
app.add_page(index)
