import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import math

class HandGestureCursorController:
    def __init__(self):
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Camera setup
        self.cap = None
        self.is_tracking = False
        self.is_camera_on = False
        
        # Cursor control variables
        self.screen_width, self.screen_height = pyautogui.size()
        self.camera_width, self.camera_height = 640, 480
        
        # Gesture recognition variables
        self.last_gesture = 'none'
        self.gesture_start_time = 0
        self.gesture_hold_time = 0.3  # Hold gesture for 300ms before action
        
        # Smoothing variables
        self.smoothing_factor = 0.7
        self.last_x, self.last_y = self.screen_width // 2, self.screen_height // 2
        
        # Dragging state
        self.is_dragging = False
        self.drag_start_pos = None
        
        # Click prevention (avoid rapid clicking)
        self.last_click_time = 0
        self.click_cooldown = 0.5
        
        # Debug mode for gesture recognition
        self.debug_mode = False
        
        # PyAutoGUI settings
        pyautogui.FAILSAFE = True  # Move mouse to corner to stop
        pyautogui.PAUSE = 0.01     # Small pause between actions
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Create the control GUI"""
        self.root = tk.Tk()
        self.root.title("Hand Gesture Cursor Controller")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        self.root.configure(bg='#2b2b2b')
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#2b2b2b', foreground='#ff4080')
        style.configure('Info.TLabel', font=('Arial', 10), background='#2b2b2b', foreground='white')
        style.configure('Status.TLabel', font=('Arial', 12), background='#2b2b2b', foreground='#00ff00')
        
        # Main title
        title_label = ttk.Label(self.root, text="🖐️ Hand Gesture Cursor Control", style='Title.TLabel')
        title_label.pack(pady=20)
        
        # Status frame
        status_frame = tk.Frame(self.root, bg='#2b2b2b')
        status_frame.pack(pady=10, padx=20, fill='x')
        
        # Camera status
        self.camera_status_label = ttk.Label(status_frame, text="📹 Camera: OFF", style='Info.TLabel')
        self.camera_status_label.pack(side='left')
        
        # Hand detection status
        self.hand_status_label = ttk.Label(status_frame, text="✋ Hands: 0", style='Info.TLabel')
        self.hand_status_label.pack(side='right')
        
        # Current gesture display
        gesture_frame = tk.Frame(self.root, bg='#3b3b3b', relief='raised', bd=2)
        gesture_frame.pack(pady=10, padx=20, fill='x')
        
        ttk.Label(gesture_frame, text="Current Gesture:", font=('Arial', 12), 
                 background='#3b3b3b', foreground='white').pack(pady=5)
        
        self.current_gesture_label = ttk.Label(gesture_frame, text="NONE", 
                                              font=('Arial', 14, 'bold'), 
                                              background='#3b3b3b', foreground='#ff4080')
        self.current_gesture_label.pack(pady=5)
        
        # Finger status display (for debugging)
        self.finger_status_frame = tk.Frame(self.root, bg='#3b3b3b', relief='raised', bd=2)
        if self.debug_mode:
            self.finger_status_frame.pack(pady=10, padx=20, fill='x')
        
        ttk.Label(self.finger_status_frame, text="Finger Status:", font=('Arial', 12), 
                 background='#3b3b3b', foreground='white').pack(pady=5)
        
        self.finger_status_label = ttk.Label(self.finger_status_frame, text="[0, 0, 0, 0, 0]", 
                                            font=('Arial', 12), 
                                            background='#3b3b3b', foreground='#4080ff')
        self.finger_status_label.pack(pady=5)
        
        # Control buttons frame
        control_frame = tk.Frame(self.root, bg='#2b2b2b')
        control_frame.pack(pady=20)
        
        # Start/Stop camera button
        self.camera_button = tk.Button(control_frame, text="Start Camera", 
                                      command=self.toggle_camera,
                                      bg='#ff4080', fg='white', font=('Arial', 12, 'bold'),
                                      width=15, height=2)
        self.camera_button.pack(side='left', padx=10)
        
        # Start/Stop tracking button
        self.tracking_button = tk.Button(control_frame, text="Start Tracking", 
                                        command=self.toggle_tracking,
                                        bg='#4080ff', fg='white', font=('Arial', 12, 'bold'),
                                        width=15, height=2, state='disabled')
        self.tracking_button.pack(side='left', padx=10)
        
        # Gesture instructions
        instructions_frame = tk.Frame(self.root, bg='#3b3b3b', relief='raised', bd=2)
        instructions_frame.pack(pady=20, padx=20, fill='both', expand=True)
        
        ttk.Label(instructions_frame, text="Gesture Controls:", 
                 font=('Arial', 14, 'bold'), background='#3b3b3b', foreground='white').pack(pady=10)
        
        instructions = [
            "👆 Index Finger → Move Cursor",
            "✌️ Two Fingers (Peace) → Left Click", 
            "✋ Open Hand → Right Click",
            "👍 Thumbs Up → Scroll Up",
            "👎 Thumbs Down → Scroll Down",
            "✊ Closed Fist → Drag Mode",
            "🤏 Pinch → Precision Mode"
        ]
        
        for instruction in instructions:
            ttk.Label(instructions_frame, text=instruction, font=('Arial', 11), 
                     background='#3b3b3b', foreground='#cccccc').pack(pady=3, anchor='w', padx=20)
        
        # Action log
        log_frame = tk.Frame(self.root, bg='#3b3b3b', relief='raised', bd=2)
        log_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        ttk.Label(log_frame, text="Action Log:", font=('Arial', 12, 'bold'), 
                 background='#3b3b3b', foreground='white').pack(pady=5)
        
        # Create scrollable text widget for log
        log_scroll_frame = tk.Frame(log_frame, bg='#3b3b3b')
        log_scroll_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_scroll_frame, height=8, bg='black', fg='#00ff00', 
                               font=('Courier', 9), wrap='word')
        log_scrollbar = tk.Scrollbar(log_scroll_frame)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)
        
        # Initial log entry
        self.log_action("System initialized. Ready to start camera.")
        
        # Close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def log_action(self, message):
        """Add message to action log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert('end', log_entry)
        self.log_text.see('end')
        
        # Keep log reasonable size
        if self.log_text.index('end-1c').split('.')[0] > '100':
            self.log_text.delete('1.0', '20.0')
    
    def toggle_camera(self):
        """Start or stop the camera"""
        if not self.is_camera_on:
            self.start_camera()
        else:
            self.stop_camera()
    
    def start_camera(self):
        """Start the camera and video processing"""
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            
            if not self.cap.isOpened():
                raise Exception("Could not open camera")
            
            self.is_camera_on = True
            self.camera_button.config(text="Stop Camera", bg='#ff4040')
            self.tracking_button.config(state='normal')
            self.camera_status_label.config(text="📹 Camera: ON", foreground='#00ff00')
            
            # Start video processing thread
            self.video_thread = threading.Thread(target=self.process_video, daemon=True)
            self.video_thread.start()
            
            self.log_action("Camera started successfully")
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            self.log_action(f"Camera error: {str(e)}")
    
    def stop_camera(self):
        """Stop the camera"""
        self.is_camera_on = False
        self.is_tracking = False
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        self.camera_button.config(text="Start Camera", bg='#ff4080')
        self.tracking_button.config(text="Start Tracking", bg='#4080ff', state='disabled')
        self.camera_status_label.config(text="📹 Camera: OFF", foreground='#ff4040')
        self.hand_status_label.config(text="✋ Hands: 0")
        self.current_gesture_label.config(text="NONE")
        
        self.log_action("Camera stopped")
    
    def toggle_tracking(self):
        """Start or stop gesture tracking"""
        self.is_tracking = not self.is_tracking
        
        if self.is_tracking:
            self.tracking_button.config(text="Stop Tracking", bg='#ff4040')
            self.log_action("Gesture tracking started")
        else:
            self.tracking_button.config(text="Start Tracking", bg='#4080ff')
            self.current_gesture_label.config(text="NONE")
            self.log_action("Gesture tracking stopped")
    
    def get_finger_states(self, landmarks):
        """Determine which fingers are extended"""
        # Get landmark positions
        tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        pips = [3, 6, 10, 14, 18]  # PIP joints (middle knuckles)
        mcps = [2, 5, 9, 13, 17]   # MCP joints (base knuckles)
        
        # Array to store finger states (1 = extended, 0 = folded)
        fingers_up = [0, 0, 0, 0, 0]
        
        # Special case for thumb (check horizontal position)
        # Thumb is extended if tip is to the right/left of the IP joint (depending on hand)
        if landmarks[tips[0]].x < landmarks[pips[0]].x:
            fingers_up[0] = 1
        
        # For other fingers, check if fingertip is above PIP joint
        for i in range(1, 5):
            # Check vertical position (y-coordinate decreases going up)
            if landmarks[tips[i]].y < landmarks[pips[i]].y:
                fingers_up[i] = 1
        
        return fingers_up
    
    def recognize_gesture(self, landmarks):
        """Recognize hand gesture from landmarks"""
        # Get finger states (extended or not)
        fingers_up = self.get_finger_states(landmarks)
        
        # Update finger status display if in debug mode
        if self.debug_mode:
            self.finger_status_label.config(text=str(fingers_up))
        
        # Count extended fingers
        total_fingers = sum(fingers_up)
        
        # Calculate distance between index and thumb tips for pinch detection
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        pinch_distance = math.sqrt(
            (thumb_tip.x - index_tip.x)**2 + 
            (thumb_tip.y - index_tip.y)**2
        )
        
        # Gesture recognition logic
        if fingers_up == [0, 1, 0, 0, 0]:  # Only index
            return 'point'
        elif fingers_up == [0, 1, 1, 0, 0]:  # Index and middle (peace)
            return 'peace'
        elif fingers_up == [1, 1, 1, 1, 1]:  # All fingers
            return 'open_hand'
        elif fingers_up == [0, 0, 0, 0, 0]:  # Fist
            return 'fist'
        elif fingers_up == [1, 0, 0, 0, 0]:  # Only thumb
            # Check if thumb is up or down
            if landmarks[4].y < landmarks[9].y:  # Compare thumb tip to middle finger MCP
                return 'thumbs_up'
            else:
                return 'thumbs_down'
        elif pinch_distance < 0.05:  # Pinch gesture (thumb and index close together)
            return 'pinch'
        
        return 'unknown'
    
    def handle_gesture(self, gesture, landmarks):
        """Handle recognized gesture and perform corresponding action"""
        current_time = time.time()
        
        # Update gesture display
        gesture_display = gesture.replace('_', ' ').upper()
        self.current_gesture_label.config(text=gesture_display)
        
        # Check if gesture changed
        if gesture != self.last_gesture:
            self.last_gesture = gesture
            self.gesture_start_time = current_time
            return
        
        # Check if gesture has been held long enough
        if current_time - self.gesture_start_time < self.gesture_hold_time:
            return
        
        # Get index finger tip for cursor positioning
        index_tip = landmarks[8]
        
        # Convert hand coordinates to screen coordinates (mirror X for natural movement)
        screen_x = int((1 - index_tip.x) * self.screen_width)
        screen_y = int(index_tip.y * self.screen_height)
        
        # Apply smoothing
        smooth_x = int(self.last_x * self.smoothing_factor + screen_x * (1 - self.smoothing_factor))
        smooth_y = int(self.last_y * self.smoothing_factor + screen_y * (1 - self.smoothing_factor))
        
        self.last_x, self.last_y = smooth_x, smooth_y
        
        # Handle different gestures
        try:
            if gesture == 'point':
                pyautogui.moveTo(smooth_x, smooth_y)
                if self.is_dragging:
                    # Continue dragging
                    pass
                    
            elif gesture == 'peace':
                # Left click with cooldown
                if current_time - self.last_click_time > self.click_cooldown:
                    self.log_action(f"Left click attempt at ({smooth_x}, {smooth_y})")
                    pyautogui.click(smooth_x, smooth_y)
                    self.last_click_time = current_time
                    
            elif gesture == 'open_hand':
                # Right click with cooldown
                if current_time - self.last_click_time > self.click_cooldown:
                    self.log_action(f"Right click attempt at ({smooth_x}, {smooth_y})")
                    pyautogui.rightClick(smooth_x, smooth_y)
                    self.last_click_time = current_time
                    
            elif gesture == 'thumbs_up':
                # Scroll up
                pyautogui.scroll(3)
                self.log_action("Scrolled up")
                self.gesture_start_time = current_time  # Reset to prevent rapid scrolling
                
            elif gesture == 'thumbs_down':
                # Scroll down
                pyautogui.scroll(-3)
                self.log_action("Scrolled down")
                self.gesture_start_time = current_time  # Reset to prevent rapid scrolling
                
            elif gesture == 'fist':
                # Start/continue dragging
                if not self.is_dragging:
                    pyautogui.mouseDown(smooth_x, smooth_y)
                    self.is_dragging = True
                    self.drag_start_pos = (smooth_x, smooth_y)
                    self.log_action(f"Started dragging from ({smooth_x}, {smooth_y})")
                else:
                    pyautogui.moveTo(smooth_x, smooth_y)
                    
            elif gesture == 'pinch':
                # Precision mode - slower movement
                precision_x = int(self.last_x * 0.9 + screen_x * 0.1)
                precision_y = int(self.last_y * 0.9 + screen_y * 0.1)
                pyautogui.moveTo(precision_x, precision_y)
                self.last_x, self.last_y = precision_x, precision_y
                
            else:
                # Stop dragging for unknown gestures
                if self.is_dragging:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                    self.log_action("Stopped dragging")
                    
        except Exception as e:
            self.log_action(f"Error performing action: {str(e)}")
    
    def process_video(self):
        """Main video processing loop"""
        while self.is_camera_on:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process hand detection
            results = self.hands.process(rgb_frame)
            
            # Update hand count
            hand_count = 0
            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
                
            self.hand_status_label.config(text=f"✋ Hands: {hand_count}")
            
            # Draw hand landmarks and handle gestures
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw landmarks
                    self.mp_draw.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # Draw finger tip markers
                    tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
                    for tip in tips:
                        tip_x = int(hand_landmarks.landmark[tip].x * frame.shape[1])
                        tip_y = int(hand_landmarks.landmark[tip].y * frame.shape[0])
                        cv2.circle(frame, (tip_x, tip_y), 10, (0, 255, 255), -1)
                    
                    # Handle gestures if tracking is enabled
                    if self.is_tracking:
                        gesture = self.recognize_gesture(hand_landmarks.landmark)
                        self.handle_gesture(gesture, hand_landmarks.landmark)
                        
                        # Display recognized gesture on frame
                        cv2.putText(frame, f"Gesture: {gesture.upper()}", 
                                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                                   (255, 255, 0), 2)
            else:
                # No hands detected
                self.current_gesture_label.config(text="NO HANDS")
                if self.is_dragging:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                    self.log_action("Stopped dragging (no hands)")
            
            # Add status overlay to video
            status_text = f"Tracking: {'ON' if self.is_tracking else 'OFF'}"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                       (0, 255, 0) if self.is_tracking else (0, 0, 255), 2)
            
            # Add peace sign indicator
            cv2.putText(frame, "Make a peace sign (✌️) to left-click", 
                       (frame.shape[1] - 400, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (255, 255, 255), 2)
            
            # Add crosshair in center
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2-20, h//2), (w//2+20, h//2), (255, 0, 255), 2)
            cv2.line(frame, (w//2, h//2-20), (w//2, h//2+20), (255, 0, 255), 2)
            
            # Show video feed
            cv2.imshow('Hand Gesture Control - Position hand in center', frame)
            
            # Break on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    def on_closing(self):
        """Handle application closing"""
        self.stop_camera()
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        try:
            self.log_action("Application started. Click 'Start Camera' to begin.")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.log_action("Application interrupted by user")
        finally:
            self.stop_camera()

# Run the application
if __name__ == "__main__":
    print("Starting Hand Gesture Cursor Controller...")
    print("Make sure you have installed the required packages:")
    print("pip install opencv-python mediapipe pyautogui")
    print()
    
    try:
        app = HandGestureCursorController()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")