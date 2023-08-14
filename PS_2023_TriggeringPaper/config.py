from datetime import datetime

shift_per_date = {
    datetime(2021,5,12,0,0): -4,
    datetime(2021,5,12,0,0): -4,
    
    
}

noise_floor = {
    "Touches": 1,
    "Reach Across": 1,
    "Clapping": 1.5,
    "Reach Out": 1,
    "Reach Diagonal": 1,
    "Supination": 3,
    "Bicep Curls": 3,
    "Shoulder Extension": 3,
    "Shoulder Abduction": 3,
    "Flyout": 3,
    "Wrist Flexion": 3,
    "Wrist Deviation": 3,
    "Grip": 1.5,
    "Rotate": 1.5,
    "Key Pinch": 1.5,
    "Finger Tap": 1,
    "Thumb Press": 1.5,
    "Finger Twists": 1.5,
    "Rolling": 1.5,
    "Flipping": 3,
    "Lift": 1,
    "Generic movement": 3,
    "Generic bidirectional movement": 3,
    "Supination and press": 1,
    "Isometric Handle": 1,
    "Isometric Knob": 1,
    "Isometric Wrist": 1,
    "Isometric Pinch": 10,
    "Isometric Pinch Left": 10,
    "Range of Motion Handle": 2,
    "Range of Motion Knob": 2,
    "Range of Motion Wrist": 2,
    "Isometric Pinch Flexion": 40,
    "Isometric Pinch Extension": 40,
    "Isometric Pinch Left Flexion": 40,
    "Isometric Pinch Left Extension": 40,
    "Touch": 1
}

def GetNoiseFloor(exerciseName):
    if exerciseName in noise_floor:
        return noise_floor[exerciseName]
    else:
        return 1