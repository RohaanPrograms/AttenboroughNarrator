import tkinter as tk
from tkinter import messagebox


class TodoApp:

    def __init__(self, root):
        self.root = root
        self.root.title("To-Do List")
        self.root.geometry("400x450")
        self.root.config(bg="#f0f0f0")

        # Title Label
        title_label = tk.Label(
            root,
            text="My To-Do List",
            font=("Arial", 18, "bold"),
            bg="#f0f0f0",
        )
        title_label.pack(pady=10)

        # Entry Box for new tasks
        self.task_entry = tk.Entry(root, font=("Arial", 12), width=25)
        self.task_entry.pack(pady=10)

        # Buttons Frame
        btn_frame = tk.Frame(root, bg="#f0f0f0")
        btn_frame.pack(pady=5)

        # Add Button
        add_btn = tk.Button(
            btn_frame,
            text="Add Task",
            command=self.add_task,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        add_btn.grid(row=0, column=0, padx=5)

        # Delete Button
        del_btn = tk.Button(
            btn_frame,
            text="Delete Selected",
            command=self.delete_task,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        del_btn.grid(row=0, column=1, padx=5)

        # Listbox to display tasks
        self.task_listbox = tk.Listbox(
            root,
            font=("Arial", 12),
            width=30,
            height=12,
            selectbackground="#a6a6a6",
        )
        self.task_listbox.pack(pady=15)

    def add_task(self):
        task = self.task_entry.get().strip()
        if task != "":
            self.task_listbox.insert(tk.END, task)
            self.task_entry.delete(0, tk.END)  # Clear entry box
        else:
            messagebox.showwarning("Warning", "You must enter a task.")

    def delete_task(self):
        try:
            selected_task_index = self.task_listbox.curselection()[0]
            self.task_listbox.delete(selected_task_index)
        except IndexError:
            messagebox.showwarning(
                "Warning", "You must select a task to delete."
            )


# Run the GUI application
if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()