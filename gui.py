"""
Orchestrated AI Hierarchy — Tkinter GUI

Usage:
    python gui.py

The agent runs in a background thread so the window stays responsive.
Agent dispatch logs stream in real-time as the hierarchy executes.
"""

import os
import sys
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

# Ensure project root is importable
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_DIR, ".env"))
except ImportError:
    pass

from orchestrator import OrchestratorAgent  # noqa: E402

# ------------------------------------------------------------------
# Colours
# ------------------------------------------------------------------
BG        = "#1e1e2e"
BG_INPUT  = "#2a2a3d"
FG        = "#cdd6f4"
TEAL      = "#94e2d5"
BLUE      = "#89b4fa"
ORANGE    = "#fab387"
GREY      = "#6c7086"
RED       = "#f38ba8"
GREEN     = "#a6e3a1"
YELLOW    = "#f9e2af"
BORDER    = "#45475a"


# ------------------------------------------------------------------
# Stdout redirector → queue
# ------------------------------------------------------------------

class _QueueStream:
    """Captures print() output from agent threads and sends it to the GUI queue."""
    def __init__(self, q: queue.Queue):
        self._q = q

    def write(self, text: str):
        stripped = text.strip()
        if stripped:
            self._q.put(("log", stripped))

    def flush(self):
        pass


# ------------------------------------------------------------------
# Main application
# ------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Orchestrated AI Hierarchy")
        self.geometry("860x640")
        self.minsize(600, 400)
        self.configure(bg=BG)

        self._q: queue.Queue = queue.Queue()
        self._busy = False

        if not os.environ.get("ANTHROPIC_API_KEY"):
            self._show_key_error()
            return

        self._orchestrator = OrchestratorAgent()
        self._build_ui()
        self._poll()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Title bar ────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg=BG, pady=8)
        title_frame.pack(fill=tk.X, padx=14)

        tk.Label(
            title_frame, text="Orchestrated AI Hierarchy",
            bg=BG, fg=BLUE, font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text="Orchestrator  ·  Research  ·  Code  ·  Data  ·  Writing",
            bg=BG, fg=GREY, font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=16, pady=2)

        # ── Chat display ──────────────────────────────────────────────
        self._chat = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10),
            bg=BG,
            fg=FG,
            insertbackground=FG,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            selectbackground=BORDER,
        )
        self._chat.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        # Text tags
        self._chat.tag_config("user",         foreground=TEAL,   font=("Consolas", 10, "bold"))
        self._chat.tag_config("log",          foreground=GREY,   font=("Consolas", 9))
        self._chat.tag_config("result_head",  foreground=BLUE,   font=("Consolas", 10, "bold"))
        self._chat.tag_config("result",       foreground=ORANGE, font=("Consolas", 10))
        self._chat.tag_config("error",        foreground=RED,    font=("Consolas", 10))
        self._chat.tag_config("sep",          foreground=BORDER)
        self._chat.tag_config("status_ok",    foreground=GREEN,  font=("Consolas", 9))

        # ── Input area ────────────────────────────────────────────────
        input_frame = tk.Frame(self, bg=BG)
        input_frame.pack(fill=tk.X, padx=14, pady=(0, 10))

        self._input = tk.Text(
            input_frame,
            height=3,
            font=("Consolas", 10),
            bg=BG_INPUT,
            fg=FG,
            insertbackground=FG,
            relief=tk.FLAT,
            padx=8,
            pady=6,
            wrap=tk.WORD,
        )
        self._input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._input.bind("<Return>",       self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)   # allow newline with Shift+Enter

        btn_frame = tk.Frame(input_frame, bg=BG)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self._send_btn = tk.Button(
            btn_frame,
            text="Send",
            width=9,
            font=("Segoe UI", 10),
            bg="#313244",
            fg=FG,
            activebackground=BORDER,
            activeforeground=FG,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._submit,
        )
        self._send_btn.pack(fill=tk.BOTH, expand=True)

        # ── Status bar ────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self,
            textvariable=self._status_var,
            bg="#181825",
            fg=GREY,
            font=("Segoe UI", 8),
            anchor=tk.W,
            padx=14,
            pady=3,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._input.focus()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_enter(self, event):
        self._submit()
        return "break"   # suppress default newline

    def _submit(self):
        task = self._input.get("1.0", tk.END).strip()
        if not task or self._busy:
            return

        self._input.delete("1.0", tk.END)
        self._append(f"You: {task}\n", "user")
        self._append("─" * 62 + "\n", "sep")

        self._busy = True
        self._send_btn.config(state=tk.DISABLED)
        self._status_var.set("Processing…")

        threading.Thread(
            target=self._run_agent,
            args=(task,),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Agent thread
    # ------------------------------------------------------------------

    def _run_agent(self, task: str):
        old_stdout = sys.stdout
        sys.stdout = _QueueStream(self._q)
        try:
            result = self._orchestrator.run(task)
            self._q.put(("result", result))
        except Exception as exc:
            self._q.put(("error", str(exc)))
        finally:
            sys.stdout = old_stdout
            self._q.put(("done", None))

    # ------------------------------------------------------------------
    # Queue polling (runs on main thread via after())
    # ------------------------------------------------------------------

    def _poll(self):
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "log":
                    self._append(payload + "\n", "log")
                elif kind == "result":
                    self._append("\nRESULT\n", "result_head")
                    self._append("─" * 62 + "\n", "sep")
                    self._append(payload + "\n", "result")
                    self._append("─" * 62 + "\n\n", "sep")
                elif kind == "error":
                    self._append(f"[Error] {payload}\n\n", "error")
                elif kind == "done":
                    self._busy = False
                    self._send_btn.config(state=tk.NORMAL)
                    self._status_var.set("Ready")
                    self._input.focus()
        except queue.Empty:
            pass
        self.after(80, self._poll)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append(self, text: str, tag: str):
        self._chat.config(state=tk.NORMAL)
        self._chat.insert(tk.END, text, tag)
        self._chat.see(tk.END)
        self._chat.config(state=tk.DISABLED)

    def _show_key_error(self):
        tk.Label(
            self,
            text=(
                "ANTHROPIC_API_KEY is not set.\n\n"
                "Add it to orchestrated_ai/.env:\n"
                "ANTHROPIC_API_KEY=sk-ant-..."
            ),
            bg=BG, fg=RED,
            font=("Consolas", 11),
            justify=tk.LEFT,
            padx=30, pady=30,
        ).pack(expand=True)


# ------------------------------------------------------------------

if __name__ == "__main__":
    App().mainloop()
