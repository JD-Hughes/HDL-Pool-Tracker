import tkinter as tk
from tkinter import ttk

def on_click():
    label_var.set("Button clicked!")

root = tk.Tk()
root.title("Tkinter Test App")
root.geometry("400x300")

# A label
label_var = tk.StringVar(value="Hello, Tkinter is working!")
label = tk.Label(root, textvariable=label_var, font=("Arial", 16), bg="yellow")
label.pack(pady=20)

# An entry
entry = ttk.Entry(root)
entry.pack(pady=10)

# A button
button = ttk.Button(root, text="Click Me", command=on_click)
button.pack(pady=10)

# A notebook with two tabs
notebook = ttk.Notebook(root)
tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)
notebook.add(tab1, text="Tab 1")
notebook.add(tab2, text="Tab 2")
notebook.pack(expand=True, fill="both", pady=20)

# Content inside tabs
tk.Label(tab1, text="This is tab 1", bg="lightblue").pack(expand=True, fill="both")
tk.Label(tab2, text="This is tab 2", bg="lightgreen").pack(expand=True, fill="both")

root.mainloop()
