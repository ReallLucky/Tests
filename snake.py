import streamlit as st
import time
import random
import streamlit.components.v1 as components

# =============================
# Konfiguration
# =============================
GRID = 20
SIZE = 400
CELL = SIZE // GRID

OPPOSITE = {
    "w": "s",
    "s": "w",
    "a": "d",
    "d": "a",
}

# =============================
# Game Init
# =============================
def init_game():
    st.session_state.snake = [(10, 10), (9, 10), (8, 10)]
    st.session_state.dir = "d"
    st.session_state.next_dir = "d"
    st.session_state.food = spawn_food()
    st.session_state.score = 0
    st.session_state.speed = 0.25
    st.session_state.game_over = False

def spawn_food():
    while True:
        p = (random.randint(0, GRID - 1), random.randint(0, GRID - 1))
        if p not in st.session_state.snake:
            return p

if "snake" not in st.session_state:
    init_game()

# =============================
# Keyboard Listener (stabil)
# =============================
key = components.html(
    """
    <script>
    document.addEventListener("keydown", e => {
        const k = e.key.toLowerCase();
        if (["w","a","s","d"].includes(k)) {
            window.parent.postMessage(
                { type: "streamlit:setComponentValue", value: k },
                "*"
            );
        }
    });
    </script>
    """,
    height=0,
)

if key and key != OPPOSITE.get(st.session_state.dir):
    st.session_state.next_dir = key

# =============================
# Game Tick
# =============================
if not st.session_state.game_over:
    st.session_state.dir = st.session_state.next_dir

    x, y = st.session_state.snake[0]
    moves = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
    dx, dy = moves[st.session_state.dir]
    new = (x + dx, y + dy)

    # Collision
    if (
        new[0] < 0 or new[0] >= GRID
        or new[1] < 0 or new[1] >= GRID
        or new in st.session_state.snake
    ):
        st.session_state.game_over = True
    else:
        st.session_state.snake.insert(0, new)

        if new == st.session_state.food:
            st.session_state.score += 1
            st.session_state.food = spawn_food()
            if st.session_state.score % 5 == 0:
                st.session_state.speed = max(0.06, st.session_state.speed - 0.02)
        else:
            st.session_state.snake.pop()

# =============================
# Render Canvas
# =============================
snake_js = "".join(
    f"ctx.fillRect({x*CELL},{y*CELL},{CELL},{CELL});"
    for x, y in st.session_state.snake
)

canvas = f"""
<canvas id="c" width="{SIZE}" height="{SIZE}"
style="background:#f7f7f7;border:1px solid #ccc"></canvas>
<script>
const c = document.getElementById("c");
const ctx = c.getContext("2d");
ctx.clearRect(0,0,{SIZE},{SIZE});

// snake
ctx.fillStyle = "green";
{snake_js}

// food
ctx.fillStyle = "red";
ctx.beginPath();
ctx.arc(
    {st.session_state.food[0]*CELL + CELL/2},
    {st.session_state.food[1]*CELL + CELL/2},
    {CELL/2 - 2},
    0, Math.PI * 2
);
ctx.fill();
</script>
"""

components.html(canvas, height=SIZE + 10)

# =============================
# UI
# =============================
st.markdown(f"### 🐍 Score: {st.session_state.score}")

if st.session_state.game_over:
    st.error("💀 Game Over")

if st.button("🔄 Neustart"):
    init_game()
    st.rerun()

time.sleep(st.session_state.speed)
st.rerun()