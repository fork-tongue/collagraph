def format_label(text, done):
    status = "done" if done else "todo"
    return f"[{status}] {text}"
