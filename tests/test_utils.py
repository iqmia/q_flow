

from flask_testing import TestCase
from q_flow.services.utils import rnd_color
from tests.base import Base
import tkinter as tk


class Test_utils(Base, TestCase):
    '''
    Test the utils routes
    '''
    def setUp(self):
        '''
        Set up the test client
        '''
        print("setting up test")
        super().setUp()

    # def test_rnd_color(self):
    #     def update_color():
    #         """
    #         Update the background color of the window with a new random dark color.
    #         """
    #         new_color = rnd_color()
    #         color_label.config(bg=new_color, text=new_color)

    #     root = tk.Tk()
    #     root.title("Random Dark Color Preview")

    #     # Create a label to display the color
    #     color_label = tk.Label(root, text="", font=("Arial", 24), width=20, height=10, foreground="white")
    #     color_label.pack(pady=20)

    #     # Create a button to generate a new color
    #     generate_button = tk.Button(root, text="Generate Dark Color", command=update_color)
    #     generate_button.pack(pady=20)

    #     # Initialize with a random dark color
    #     update_color()

    #     # Run the tkinter main loop
    #     root.mainloop()
