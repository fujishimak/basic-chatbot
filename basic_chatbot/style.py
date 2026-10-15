# style.py
from rich.jupyter import display
import reflex as rx

chat_margin = "12%"
message_style = dict(
    padding="0.875em 1em",
    border_radius="16px",
    margin_y="0.5em",
    max_width="34em",
    display="inline-block",
    overflow_wrap="anywhere",
    line_height="1.65",
    font_size="0.95rem",
    text_align="left",
)
question_style = message_style | dict(
    margin_left=chat_margin,
    background_color=rx.color("accent", 3),
    color=rx.color("accent", 12),
    border=f"1px solid {rx.color('accent', 5)}",
    #display='block',
    align_self="end"
)
answer_style = message_style | dict(
    margin_right=chat_margin,
    background_color=rx.color("slate", 2),
    color=rx.color("slate", 12),
    border=f"1px solid {rx.color('slate', 4)}",
    #display='block',
)
input_style = dict(
    width="100%",
    min_width="0",
    flex="1",
    height="44px",
    border_radius="12px",
    background_color=rx.color("slate", 1),
    border=f"1px solid {rx.color('slate', 7)}",
    box_shadow="none",
    **{
        "& input": {
            "padding": "0 14px",
            "font_size": "14px",
            "border": "none",
            "outline": "none",
            "box_shadow": "none",
            "background": "transparent",
        },
        "& input::placeholder": {"color": rx.color("slate", 11)},
        "&:focus-within": {
            "border_color": rx.color("accent", 8),
            "box_shadow": f"0 0 0 3px {rx.color('accent', 3)}",
        },
    },
)
button_style = dict(
    flex_shrink="0",
    height="44px",
    padding="0 20px",
    border_radius="12px",
    font_weight="600",
    background_color=rx.color("accent", 9),
    color="white",
    cursor="pointer",
    _hover={"background_color": rx.color("accent", 10)},
    _disabled={"opacity": "0.65", "cursor": "not-allowed"},
)
index_style = dict(
    width="100%",
    max_width="48em",
    height="100dvh", # fill the entire height of the viewport (responsive on mobile as well)
    margin="0 auto", # center horizontally
    padding="1em",
    display="flex", # move away from default block flow and control how space is used by children
    flex_direction="column" # stacks children vertically
    # align="stretch", flex handles width in this case
)