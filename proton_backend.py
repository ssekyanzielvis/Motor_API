# proton_backend.py
from flask import Flask, jsonify, request
import requests
import os
import time

app = Flask(__name__)

# --- Configuration ---
MOCK_MOTOR_CONTROL_URL = os.environ.get("MOCK_MOTOR_CONTROL_URL", "http://localhost:5001")

# --- Backend Service Layer (Interacts with Mock Motor Control) ---
class MotorControlService:
    def __init__(self, base_url):
        self.base_url = base_url

    def _send_command(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            if data:
                response = requests.post(url, json=data)
            else:
                response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            return response.json(), response.status_code
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to mock motor control service."}, 503
        except requests.exceptions.Timeout:
            return {"error": "Mock motor control service timed out."}, 504
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP error from mock service: {e.response.text}"}, e.response.status_code
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}, 500

    def get_vehicle_status(self):
        return self._send_command("motor/status")

    def turn_motor_on(self):
        return self._send_command("motor/power", {"on": True})

    def turn_motor_off(self):
        return self._send_command("motor/power", {"on": False})

    def set_vehicle_speed(self, target_speed_kph):
        if not isinstance(target_speed_kph, (int, float)) or not (0 <= target_speed_kph <= 80):
            return {"error": "Invalid target speed. Must be a number between 0 and 80."}, 400
        return self._send_command("motor/speed", {"target_speed_kph": target_speed_kph})

    def set_vehicle_direction(self, direction):
        if direction not in ["forward", "reverse", "neutral"]:
            return {"error": "Invalid direction. Must be 'forward', 'reverse', or 'neutral'."}, 400
        return self._send_command("motor/direction", {"direction": direction})

    def apply_vehicle_brake(self, force):
        if not isinstance(force, (int, float)) or not (0 <= force <= 1):
            return {"error": "Invalid brake force. Must be between 0 and 1."}, 400
        return self._send_command("motor/brake", {"force": force})

    def set_vehicle_steering(self, angle):
        if not isinstance(angle, (int, float)) or not (-90 <= angle <= 90):
            return {"error": "Invalid steering angle. Must be between -90 and 90."}, 400
        return self._send_command("motor/steering", {"angle": angle})

    def set_charging_status(self, solar=None, grid=None):
        payload = {}
        if solar is not None:
            payload['solar'] = solar
        if grid is not None:
            payload['grid'] = grid
        if not payload:
            return {"error": "No charging status provided (solar or grid)."}, 400
        return self._send_command("vehicle/charge", payload)

    def set_security_lock(self, lock_status):
        if not isinstance(lock_status, bool):
            return {"error": "Invalid lock status. Must be boolean."}, 400
        return self._send_command("security/lock", {"lock": lock_status})

# Initialize the service
motor_service = MotorControlService(MOCK_MOTOR_CONTROL_URL)

# --- Proton Backend API Endpoints ---

@app.route('/api/vehicle/status', methods=['GET'])
def get_status():
    """Retrieves the current status of the Proton vehicle."""
    response_data, status_code = motor_service.get_vehicle_status()
    return jsonify(response_data), status_code

@app.route('/api/vehicle/control/power', methods=['POST'])
def control_power():
    """Endpoint to turn the vehicle motor on/off."""
    data = request.json
    power_on = data.get('on')
    if power_on is None:
        return jsonify({"error": "Missing 'on' parameter (boolean)."}), 400

    if power_on:
        response_data, status_code = motor_service.turn_motor_on()
    else:
        response_data, status_code = motor_service.turn_motor_off()
    return jsonify(response_data), status_code

@app.route('/api/vehicle/control/speed', methods=['POST'])
def control_speed():
    """Endpoint to set the target speed of the vehicle."""
    data = request.json
    target_speed = data.get('target_speed_kph')
    if target_speed is None:
        return jsonify({"error": "Missing 'target_speed_kph' parameter."}), 400

    response_data, status_code = motor_service.set_vehicle_speed(target_speed)
    return jsonify(response_data), status_code

@app.route('/api/vehicle/control/direction', methods=['POST'])
def control_direction():
    """Endpoint to set the direction of the vehicle."""
    data = request.json
    direction = data.get('direction')
    if direction is None:
        return jsonify({"error": "Missing 'direction' parameter ('forward', 'reverse', 'neutral')."}), 400

    response_data, status_code = motor_service.set_vehicle_direction(direction)
    return jsonify(response_data), status_code

@app.route('/api/vehicle/control/brake', methods=['POST'])
def control_brake():
    """Endpoint to apply brake force to the vehicle."""
    data = request.json
    force = data.get('force')
    if force is None:
        return jsonify({"error": "Missing 'force' parameter (0.0-1.0)."}), 400

    response_data, status_code = motor_service.apply_vehicle_brake(force)
    return jsonify(response_data), status_code

@app.route('/api/vehicle/control/steering', methods=['POST'])
def control_steering():
    """Endpoint to set the steering angle of the vehicle."""
    data = request.json
    angle = data.get('angle')
    if angle is None:
        return jsonify({"error": "Missing 'angle' parameter (-90 to 90)."}), 400

    response_data, status_code = motor_service.set_vehicle_steering(angle)
    return jsonify(response_data), status_code

@app.route('/api/vehicle/charging', methods=['POST'])
def manage_charging():
    """Endpoint to set vehicle charging status (solar/grid)."""
    data = request.json
    solar = data.get('solar')
    grid = data.get('grid')

    response_data, status_code = motor_service.set_charging_status(solar=solar, grid=grid)
    return jsonify(response_data), status_code

@app.route('/api/vehicle/security', methods=['POST'])
def manage_security():
    """Endpoint to lock or unlock the vehicle."""
    data = request.json
    lock_status = data.get('lock')
    if lock_status is None:
        return jsonify({"error": "Missing 'lock' parameter (boolean)."}), 400

    response_data, status_code = motor_service.set_security_lock(lock_status)
    return jsonify(response_data), status_code


# --- Main Runner ---
if __name__ == '__main__':
    # Run the backend server on port 5000 (default for Flask)
    print("Starting Proton Backend Service on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)