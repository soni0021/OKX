import tkinter as tk

def main():
    """Test if Tkinter is working correctly."""
    root = tk.Tk()
    root.title("Tkinter Test")
    root.geometry("300x200")
    
    label = tk.Label(root, text="If you can see this, Tkinter is working!")
    label.pack(expand=True)
    
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Tkinter error: {e}")
        print("Failed to initialize Tkinter. Please check your installation.") 