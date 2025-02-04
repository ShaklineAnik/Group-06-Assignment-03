import cv2
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import numpy as np

class ImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processing App(Sydney-06)")

        # Variables to store images
        self.original_image = None
        self.display_image = None
        self.cropped_image = None
        self.history = []  # Undo history
        self.future = []  # Redo history
        self.crop_start = None
        self.crop_end = None
        self.cropping_style = "Freeform"
        self.quality = 100  # Default quality for saving
        self.preview_image = None  # To store resized preview

        # GUI Layout
        self.create_gui()
        self.bind_shortcuts()

    def create_gui(self):
        ttk.Button(self.root, text="Upload Image", command=self.load_image).pack(pady=5)

        self.canvas = tk.Canvas(self.root, width=600, height=370, bg="black")
        self.canvas.pack()

        ttk.Label(self.root, text="Cropping Style:").pack(pady=5)
        self.cropping_style_var = tk.StringVar(value="Freeform")
        ttk.Combobox(
            self.root,
            textvariable=self.cropping_style_var,
            values=["Freeform", "1:1 (Square)", "16:9 (Widescreen)", "4:3 Style", "Circle"]
        ).pack(pady=5)

        ttk.Label(self.root, text="Image Quality Resizer").pack(pady=5)
        self.quality_slider = tk.Scale(
            self.root, from_=10, to=100, orient=tk.HORIZONTAL, command=self.update_quality
        )
        self.quality_slider.set(50)
        self.quality_slider.pack(pady=5)

        ttk.Label(self.root, text="Resize Preview").pack(pady=5)
        self.resize_slider = tk.Scale(
            self.root, from_=10, to=200, orient=tk.HORIZONTAL, command=self.update_preview
        )
        self.resize_slider.set(100)  # Default to 100% size
        self.resize_slider.pack(pady=5)

        # Undo/Redo buttons
        undo_button = ttk.Button(self.root, text="Undo", command=self.undo)
        undo_button.pack(pady=5)

        redo_button = ttk.Button(self.root, text="Redo", command=self.redo)
        redo_button.pack(pady=5)

        ttk.Button(self.root, text="Save Image", command=self.save_image).pack(pady=5)
        ttk.Button(self.root, text="Rotate Image 90°", command=self.rotate_image).pack(pady=5)

    def bind_shortcuts(self):
        self.root.bind("<Command-s>", lambda event: self.save_image())
        self.root.bind("<Command-z>", lambda event: self.undo())
        self.root.bind("<Command-Shift-Z>", lambda event: self.redo())
        self.root.bind("<Command-r>", lambda event: self.rotate_image())

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.jpeg *.bmp")])
        if not file_path:
            return

        # Load the image
        self.original_image = cv2.imread(file_path)
        self.display_image = self.original_image.copy()
        self.display_image_on_canvas(self.display_image)

        # Save initial state for undo/redo
        self.save_history(self.original_image)

        # Set mouse callback for cropping
        cv2.namedWindow("Crop Image")
        cv2.setMouseCallback("Crop Image", self.crop_image_callback)
        cv2.imshow("Crop Image", self.original_image)

    def display_image_on_canvas(self, image):
        """Convert OpenCV image to Tkinter format and display it."""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        self.canvas.create_image(250, 200, image=self.tk_image, anchor=tk.CENTER)

    def crop_image_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.crop_start = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and self.crop_start:
            temp_image = self.display_image.copy()
            self.crop_end = (x, y)
            self.show_cropping_area(temp_image)

        elif event == cv2.EVENT_LBUTTONUP:
            self.crop_end = (x, y)
            self.apply_cropping()

    def show_cropping_area(self, image):
        """Display cropping region dynamically while dragging."""
        if not self.crop_start or not self.crop_end:
            return

        x1, y1 = self.crop_start
        x2, y2 = self.crop_end
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        if x1 == x2 or y1 == y2:
            return

        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.imshow("Crop Image", image)

    def apply_cropping(self):
        """Perform cropping after user selection."""
        if not self.crop_start or not self.crop_end:
            print("⚠ Cropping not initiated properly.")
            return

        x1, y1 = self.crop_start
        x2, y2 = self.crop_end

        # Ensure valid coordinates (sort to get proper x1, y1 as the top-left corner)
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        # Ensure the coordinates are within image bounds
        height, width = self.original_image.shape[:2]
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)

        # Check if the crop region has a valid size (no zero-width or zero-height crops)
        if x2 <= x1 or y2 <= y1:
            print("⚠ Invalid cropping region. Please select a valid area.")
            return

        # Apply cropping based on the selected style
        if self.cropping_style_var.get() == "Freeform":
            # Freeform cropping: allow arbitrary rectangular region
            self.cropped_image = self.original_image[y1:y2, x1:x2]

        elif self.cropping_style_var.get() == "1:1 (Square)":
            # Apply square cropping
            size = min(x2 - x1, y2 - y1)
            self.cropped_image = self.original_image[y1:y1 + size, x1:x1 + size]

        elif self.cropping_style_var.get() == "16:9 (Widescreen)":
            # Apply 16:9 aspect ratio
            width = x2 - x1
            height = int(width * 9 / 16)
            if y1 + height > self.original_image.shape[0]:
                height = self.original_image.shape[0] - y1
            self.cropped_image = self.original_image[y1:y1 + height, x1:x2]

        elif self.cropping_style_var.get() == "4:3":
            # Apply 4:3 aspect ratio
            width = x2 - x1
            height = int(width * 3 / 4)
            if y1 + height > self.original_image.shape[0]:
                height = self.original_image.shape[0] - y1
            # Ensure that the crop respects the 4:3 ratio
            self.cropped_image = self.original_image[y1:y1 + height, x1:x2]

        elif self.cropping_style_var.get() == "Circle":
            # Apply circular crop
            radius = min(x2 - x1, y2 - y1) // 2
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            mask = np.zeros_like(self.original_image, dtype=np.uint8)
            cv2.circle(mask, center, radius, (255, 255, 255), -1)
            self.cropped_image = cv2.bitwise_and(self.original_image, mask)

        # Display cropped image if valid
        if self.cropped_image is not None and self.cropped_image.size > 0:
            self.update_preview(self.resize_slider.get())  # Update the preview with the current slider value
            self.save_history(self.cropped_image)
        else:
            print("⚠ Cropping failed or resulted in an empty image.")

    def update_quality(self, value):
        self.quality = int(value)

    def update_preview(self, value):
        """Update the preview image based on slider value (resize only preview)."""
        if self.cropped_image is not None:
            scale_percent = int(value)  # Ensure the slider value is treated as an integer
            width = int(self.cropped_image.shape[1] * scale_percent / 100)
            height = int(self.cropped_image.shape[0] * scale_percent / 100)
            self.preview_image = cv2.resize(self.cropped_image, (width, height))
            self.display_image_on_canvas(self.preview_image)

    def save_history(self, image):
        """Save image state for undo/redo functionality."""
        self.history.append(image.copy())
        self.future.clear()

    def undo(self):
        """Undo last action."""
        if len(self.history) > 1:
            self.future.append(self.history.pop())  # Move last action to redo stack
            self.display_image = self.history[-1]
            self.display_image_on_canvas(self.display_image)
            print("✅ Undo performed.")
        else:
            print("⚠ No more actions to undo.")

    def redo(self):
        """Redo the last undone action."""
        if self.future:
            self.history.append(self.future.pop())  # Restore last undone action
            self.display_image = self.history[-1]
            self.display_image_on_canvas(self.display_image)
            print("✅ Redo performed.")
        else:
            print("⚠ No more actions to redo.")

    def save_image(self):
        """Save the cropped image to a file."""
        if self.cropped_image is not None:
            file_path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                     filetypes=[("JPEG files", "*.jpg"),
                                                                ("PNG files", "*.png"),
                                                                ("All files", "*.*")])
            if file_path:
                cv2.imwrite(file_path, self.cropped_image, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
                print(f"✅ Image saved to {file_path}")

    def rotate_image(self):
        """Rotate the image by 90 degrees."""
        if self.cropped_image is not None:
            self.cropped_image = cv2.rotate(self.cropped_image, cv2.ROTATE_90_CLOCKWISE)
            self.update_preview(self.resize_slider.get())
            print("✅ Image rotated 90°.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root)
    root.mainloop()