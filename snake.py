import streamlit as st
import time
import random
import streamlit.components.v1 as components

# -----------------------------
# Konfiguration
# -----------------------------
GRID_SIZE = 20
PIXELS = 400
CELL = PIXELS // GRID_SIZE

# -----------------------------
# Session State initialisieren
# -----------------------------
def init_game():
    st.session_state.snake = [(10, 10), (9, 10), (8, 10)]
    st.session_state.direction = "d"
    st.session_state.food = spawn_food()
    st.session_state.score = 0
    st.session_state.speed = 0.25
    st.session_state.game_over = False

def spawn_food():
    while True:
        pos = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        if pos not in st.session_state.get("snake", []):
            return pos

if "snake" not in st.session_state:
    init_game()

# -----------------------------
# Steuerung aus JS übernehmen
# -----------------------------
key = components.html(
    """
    <script>
    const streamlitKey = (key) => {
        window.parent.postMessage(
            { type: "streamlit:setComponentValue", value: key },
            "*"
        );
    };

    window.addEventListener("keydown", (e) => {
        if (["w","a","s","d"].includes(e.key)) {
            streamlitKey(e.key);
        }
    });
    </script>
    """,
    height=0,
)

if key in ["w", "a", "s", "d"]:
    st.session_state.direction = key

# -----------------------------
# Spiellogik
# -----------------------------
if not st.session_state.game_over:
    head_x, head_y = st.session_state.snake[0]

    moves = {
        "w": (0, -1),
        "s": (0, 1),
        "a": (-1, 0),
        "d": (1, 0),
    }

    dx, dy = moves[st.session_state.direction]
    new_head = (head_x + dx, head_y + dy)

    # Kollision
    if (
        new_head[0] < 0
        or new_head[0] >= GRID_SIZE
        or new_head[1] < 0
        or new_head[1] >= GRID_SIZE
        or new_head in st.session_state.snake
    ):
        st.session_state.game_over = True
    else:
        st.session_state.snake.insert(0, new_head)

        if new_head == st.session_state.food:
            st.session_state.score += 1
            st.session_state.food = spawn_food()
            if st.session_state.score % 5 == 0:
                st.session_state.speed = max(0.05, st.session_state.speed - 0.02)
        else:
            st.session_state.snake.pop()

# -----------------------------
# Canvas Rendering
# -----------------------------
canvas_html = f"""
<canvas id="game" width="{PIXELS}" height="{PIXELS}"
style="border:1px solid #ccc; background:#f9f9f9"></canvas>

<script>
const c = document.getElementById("game");
const ctx = c.getContext("2d");

ctx.clearRect(0,0,{PIXELS},{PIXELS});

// Snake
ctx.fillStyle = "green";
{''.join([f'ctx.fillRect({x*CELL},{y*CELL},{CELL},{CELL});' for x,y in st.session_state.snake])}

// Food
ctx.fillStyle = "red";
ctx.beginPath();
ctx.arc(
    {st.session_state.food[0]*CELL + CELL//2},
    {st.session_state.food[1]*CELL + CELL//2},
    {CELL//2 - 2},
    0,
    Math.PI * 2
);
ctx.fill();
</script>
"""

components.html(canvas_html, height=PIXELS + 10)

# -----------------------------
# UI
# -----------------------------
st.markdown(f"### 🐍 Score: {st.session_state.score}")

if st.session_state.game_over:
    st.error("💀 Game Over")

if st.button("🔄 Neustart"):
    init_game()

time.sleep(st.session_state.speed)
st.rerun()