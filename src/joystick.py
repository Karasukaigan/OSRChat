# ./src/joystick.py
import threading
import time
import inputs
import serial

class JoystickController:
    def __init__(self):
        self.joystick_running = False
        self.joystick_thread = None
        self.current_mode = "serial"  # Default mode
        self.serial_device = None

    def start_joystick(self):
        """Start joystick control"""
        if self.joystick_running:
            return {"message": "Joystick already running"}
        
        self.joystick_running = True
        self.joystick_thread = threading.Thread(target=self._joystick_loop, daemon=True)
        self.joystick_thread.start()
        return {"message": "Joystick control started"}

    def stop_joystick(self):
        """Stop joystick control"""
        self.joystick_running = False
        return {"message": "Joystick control stopped"}

    def joystick_status(self):
        """Get joystick control status"""
        return {
            "running": self.joystick_running,
            "available": len(inputs.devices.gamepads) > 0 if hasattr(inputs, 'devices') else False
        }

    def _joystick_loop(self):
        """Joystick control loop"""
        def cleanup():
            self.joystick_running = False

        if self.current_mode == "udp":
            cleanup()
            return

        half_range_mode = False  # Half-range mode, only use the lower half of the joystick, disabled by default

        # Check joystick connection
        if not inputs.devices.gamepads:
            print("No joysticks detected at startup")
            cleanup()
            return
        print(f"Detected {len(inputs.devices.gamepads)} joystick(s)")
        
        sender = None
        ser = None
        
        def init_sender():
            """Initialize sender"""
            nonlocal sender, ser
            try:
                ser = serial.Serial(self.serial_device, 115200, timeout=0.1)  # Reduce timeout
                sender = lambda data: ser.write(data if isinstance(data, bytes) else data.encode('utf-8'))
                print(f"Initialized Serial sender to {self.serial_device}")
                return True
            except Exception as e:
                print(f"Failed to initialize sender: {e}")
                return False

        try:
            if not init_sender():
                cleanup()
                return
                
            # Initialize axis values
            left_stick_y = 0.0
            last_left_stick_y = None
            deadzone = 0.1
            send_interval = 0.02  # Send interval 20ms
            last_send_time = 0
            print("Joystick loop started, sending data every 20ms")
            scale_args = (-1.00, 1.00, 0, 9999)
            scale_args_half = (-1.00, 0.00, 0, 9999)
            
            while self.joystick_running:
                events = inputs.get_gamepad()
                updated = False
                for event in events:
                    if event.code == 'ABS_Y':
                        # Convert raw value to -1.0 to 1.0
                        raw_value = event.state / 32767.0
                        if abs(raw_value) < deadzone:
                            left_stick_y = 0.0
                        else:
                            if raw_value > 0:
                                left_stick_y = (raw_value - deadzone) / (1.0 - deadzone)
                            else:
                                left_stick_y = (raw_value + deadzone) / (1.0 - deadzone)
                            left_stick_y = max(-1.0, min(1.0, left_stick_y))
                        left_stick_y = round(left_stick_y, 2)
                        updated = True
                current_time = time.perf_counter()
                if updated or current_time - last_send_time >= send_interval:
                    # Only send command when left_stick_y differs from the last sent value
                    if last_left_stick_y is None or abs(left_stick_y - last_left_stick_y) > 0.001:
                        if half_range_mode:
                            scaled_value = self._scale_value(left_stick_y, *scale_args_half)
                        else:
                            scaled_value = self._scale_value(left_stick_y, *scale_args)
                        tcode = f"L0{scaled_value}\n".encode('utf-8')   
                        try:
                            sender(tcode)
                            # print(f"Sent: L0{scaled_value}, Stick Value: {left_stick_y:.2f}")
                        except Exception as e:
                            print(f"Failed to send data: {e}")
                            if ser:
                                ser.close()
                                ser = None
                            if not init_sender():
                                break
                        last_left_stick_y = left_stick_y
                    last_send_time = current_time
                time.sleep(0.001)  # Sleep 1ms  
        except Exception as e:
            print(f"Joystick loop error: {e}")
        finally:
            if 'ser' in locals() and ser:
                ser.close()
            cleanup()
            print("Joystick loop terminated")

    def _scale_value(self, v, i_min=-1.0, i_max=1.0, o_min=0, o_max=9999):
        if i_min >= i_max or o_min >= o_max:
            raise ValueError("Invalid range")
        return round((max(i_min, min(v, i_max)) - i_min) * (o_max - o_min) / (i_max - i_min) + o_min)