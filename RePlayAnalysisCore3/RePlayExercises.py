from enum import Enum
from py_linq import Enumerable

class RePlayDevice(Enum):
    ReCheck = 0
    FitMi = 1
    Touchscreen = 2
    Keyboard = 3
    ReTrieve = 4
    Unknown = 5

class RePlayExercises:

        @staticmethod
        def get_all_variables():
            result_variables = []
            result_variables.extend(RePlayExercises.selectable_variables_common_independent)
            result_variables.extend(RePlayExercises.selectable_variables_common_dependent)

            for selected_game in RePlayExercises.selectable_games:
                if (selected_game in RePlayExercises.selectable_variables.keys()):
                    this_game_variables = RePlayExercises.selectable_variables[selected_game]
                    for v in this_game_variables:
                        result_variables.append("(" + selected_game + ") " + v)
            
            return result_variables

        @staticmethod
        def get_available_variables_for_game(selected_game):
            result_variables = []
            result_variables.extend(RePlayExercises.selectable_variables_common_independent)
            result_variables.extend(RePlayExercises.selectable_variables_common_dependent)

            if (selected_game != "All"):
                if (selected_game in RePlayExercises.selectable_variables.keys()):
                    this_game_variables = RePlayExercises.selectable_variables[selected_game]
                    for v in this_game_variables:
                        result_variables.append("(" + selected_game + ") " + v)
            
            return result_variables

        @staticmethod
        def strip_game_name_from_variable_name (variable_name):
            pass

        #Tuple indices:
        #   0. Exercise name
        #   1. Exercise device
        #   2. Is a force-based exercise?
        #   3. Standard unit of measurement for this exercise

        exercises = [

            #ReCheck exercises
            ("Range of Motion Handle", RePlayDevice.ReCheck, False, "Degrees"),
            ("Range of Motion Knob", RePlayDevice.ReCheck, False, "Degrees"),
            ("Range of Motion Wrist", RePlayDevice.ReCheck, False, "Degrees"),

            ("Isometric Handle", RePlayDevice.ReCheck, True, "Newton cm"),
            ("Isometric Knob", RePlayDevice.ReCheck, True, "Newton cm"),
            ("Isometric Wrist", RePlayDevice.ReCheck, True, "Newton cm"),

            ("Isometric Pinch", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Flexion", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Extension", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left Flexion", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left Extension", RePlayDevice.ReCheck, True, "Grams"),

            #Touchscreen exercises
            ("Touch", RePlayDevice.Touchscreen, False, "Pixels"),

            #Keyboard exercises
            ("Typing", RePlayDevice.Keyboard, False, "Keys"),
            ("Typing (left handed words)", RePlayDevice.Keyboard, False, "Keys"),
            ("Typing (right handed words)", RePlayDevice.Keyboard, False, "Keys"),

            #ReTrieve
            ("ReTrieve", RePlayDevice.ReTrieve, "Unknown"),  

            #FitMi exercises
            ("Touches", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Clapping", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Across", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Out", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Diagonal", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Grip", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Key Pinch", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Finger Tap", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Thumb Press", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),

            ("Flipping", RePlayDevice.FitMi, False, "Degrees"),
            ("Supination", RePlayDevice.FitMi, False, "Degrees"),

            ("Bicep Curls", RePlayDevice.FitMi, False, "Degrees"),
            ("Rolling", RePlayDevice.FitMi, False, "Degrees"),
            ("Shoulder Abduction", RePlayDevice.FitMi, False, "Degrees"),
            ("Shoulder Extension", RePlayDevice.FitMi, False, "Degrees"),
            ("Wrist Deviation", RePlayDevice.FitMi, False, "Degrees"),
            
            ("Finger Twists", RePlayDevice.FitMi, False, "Degrees"),
            ("Flyout", RePlayDevice.FitMi, False, "Degrees"),
            ("Rotate", RePlayDevice.FitMi, False, "Degrees"),
            ("Wrist Flexion", RePlayDevice.FitMi, False, "Degrees"),
            
            ("Lift", RePlayDevice.FitMi, False, "Unknown"),

            ("Generic movement", RePlayDevice.FitMi, False, "Percent of 180 Degrees"),
            ("Generic bidirectional movement", RePlayDevice.FitMi, False, "Percent of 180 Degrees"),

            #Unknown exercise
            ("Unknown", RePlayDevice.Unknown, False, "Unknown")
        ]

        recheck_shorthand_name_map = {
            "Range of Motion Knob" : "ROMK",
            "Range of Motion Handle" : "ROMH",
            "Range of Motion Wrist" : "ROMW",
            "Isometric Knob" : "ISOK",
            "Isometric Handle" : "ISOH",
            "Isometric Wrist" : "ISOW",
            "Isometric Pinch" : "ISOP",
            "Isometric Pinch Left" : "ISOP"
        }        

        selectable_exercises = [

            #All exercises
            "All",

            #ReCheck exercises
            "Range of Motion Handle",
            "Range of Motion Knob",
            "Range of Motion Wrist",

            "Isometric Handle",
            "Isometric Knob",
            "Isometric Wrist",

            "Isometric Pinch",
            "Isometric Pinch Left",
            "Isometric Pinch Flexion",
            "Isometric Pinch Extension",
            "Isometric Pinch Left Flexion",
            "Isometric Pinch Left Extension",

            #Touchscreen exercises
            "Touch",

            #Keyboard exercises
            "Typing",
            "Typing (left handed words)",
            "Typing (right handed words)",      

            #ReTrieve
            "ReTrieve",  

            #FitMi exercises
            "Touches",
            "Clapping",
            "Reach Across",
            "Reach Out",
            "Reach Diagonal",
            "Grip",
            "Key Pinch",
            "Finger Tap",
            "Thumb Press",

            "Flipping",
            "Supination",

            "Bicep Curls",
            "Rolling",
            "Shoulder Abduction",
            "Shoulder Extension",
            "Wrist Deviation",
            
            "Finger Twists",
            "Flyout",
            "Rotate",
            "Wrist Flexion",
            
            "Lift",

            "Generic movement",
            "Generic bidirectional movement",

            #Unknown exercise
            "Unknown"
        ]        

        selectable_games = ["All",
            "RepetitionsMode",
            "Breakout",
            "TrafficRacer", 
            "SpaceRunner", 
            "FruitArchery", 
            "FruitNinja", 
            "TyperShark", 
            "ReTrieve", 
            "ReCheck",
            "Manual Stimulation"
        ]

        selectable_variables_common_independent = [
            "Gain",
            "Difficulty", 
            "Duration"
        ]

        selectable_variables_common_dependent = [
            "VNS trigger events [logged by ReStore]",
            "VNS trigger events [logged by RePlay]",
            "VNS trigger requests [logged by RePlay]",
            "Total repetitions",
            "Max real-world units",
            "Mean real-world units",
            "Mean peak real-world units",
            "Median peak real-world units",
            "Interdecile range of signal in real-world units"               
        ]

        selectable_variables = {
            "RepetitionsMode" : [
                "Mean peak-to-peak",
                "Median peak-to-peak"
            ],

            "ReCheck" : [
                "Mean peak-to-peak",
                "Median peak-to-peak"
            ],

            "Breakout" : [
                "Number of balls lost",
                "Balls lost per minute",
                "Longest ball duration",
                "Average ball interval",
                "Time to first ball lost",
                "Score",
                "Score - points per minute"
            ],

            "TrafficRacer" : [
                "Percent time in target lane"
                "Score per attempt - best",
                "Score per attempt - average",
                "Score - points per minute",
                "Total crashes",
                "Crashes per minute",
                "Total coins",
                "Coins per minute",
                "Coins missed",
                "Coins missed per minute",
                "Percent coins collected"
            ], 

            "SpaceRunner" : [
                "Number of attempts",
                "Attempts per minute",
                "Mean score per attempt",
                "Best attempt score",
                "Mean duration per attempt",
                "Best attempt duration",
                "Mean coins per attempt",
                "Best coins of attempt",
                "Score - points per minute"                
            ], 

            "FruitArchery" : [
                "Total fruit hit",
                "Fruit hit per minute",
                "Score",
                "Score - points per minute",
                "Shots missed per minute"
            ], 

            "FruitNinja" : [
                "Total fruit hit",
                "Swipe accuracy",
                "Score",
                "Score - points per minute",
                "Fruit missed per minute",
                "Bombs hit per minute"
            ], 

            "TyperShark" : [
                "Total sharks killed",
                "Percent sharks killed",
                "Total words completed",
                "Percent words completed",
                "Total keypresses",
                "Percent accurate keypresses",
                "Words per minute",
                "Keys per minute",
                "Correct keys per minute",
                "Mistakes per minute",
            ], 

            "ReTrieve" : [
                "Percent correct",
                "Retrieval rate",
                "Success rate",
                "Mean search time per object",
                "Total search time"
            ]
        }

        selectable_hand = [
            "Both",
            "Left",
            "Right"
        ]

        yes_or_no_response = [
            "Yes",
            "No"
        ]        

        game_name_color_palette = {
            "RepetitionsMode" : "#E41A1C",
            "Breakout" : "#377EB8", 
            "TrafficRacer" : "#4DAF4A", 
            "SpaceRunner": "#984EA3", 
            "FruitArchery": "#FF7F00", 
            "FruitNinja": "#FFFF33", 
            "TyperShark": "#A65628", 
            "ReTrieve": "#F781BF", 
            "ReCheck": "#999999",
            "Manual Stimulation": "#555555"
        }

        exercise_category_color_palette = {
            "FitMi Force" : "#FFEC16",
            "FitMi Flip" : "#3D4DB7",
            "FitMi Arm" : "#1093F5",
            "FitMi Twist" : "#00A7F6",
            "FitMi Lift" : "#9C1AB1",
            "FitMi Generic" : "#00BBD5",
            "ReCheck ROM" : "#46AF4A",
            "ReCheck Isometric" : "#F6402C",
            "ReCheck Pinch" : "#FF9800",
            "Touchscreen" : "#795446",
            "Keyboard" : "#9D9D9D",
            "Unknown" : "#000000"
        }

        fitmi_exercises = [
            "Touches",
            "Clapping",
            "Reach Across",
            "Reach Out",
            "Reach Diagonal",
            "Grip",
            "Key Pinch",
            "Finger Tap",
            "Thumb Press",

            "Flipping",
            "Supination",

            "Bicep Curls",
            "Rolling",
            "Shoulder Abduction",
            "Shoulder Extension",
            "Wrist Deviation",
            
            "Finger Twists",
            "Flyout",
            "Rotate",
            "Wrist Flexion",
            
            "Lift",

            "Generic movement",
            "Generic bidirectional movement",
        ]

        recheck_exercises = [
            "Range of Motion Handle",
            "Range of Motion Knob",
            "Range of Motion Wrist",

            "Isometric Handle",
            "Isometric Knob",
            "Isometric Wrist",

            "Isometric Pinch",
            "Isometric Pinch Left",
            "Isometric Pinch Flexion",
            "Isometric Pinch Extension",
            "Isometric Pinch Left Flexion",
            "Isometric Pinch Left Extension",            
        ]

        exercise_name_category_map = {

            "Touches" : "FitMi Force",
            "Clapping" : "FitMi Force",
            "Reach Across" : "FitMi Force",
            "Reach Out" : "FitMi Force",
            "Reach Diagonal" : "FitMi Force",
            "Grip" : "FitMi Force",
            "Key Pinch" : "FitMi Force",
            "Finger Tap" : "FitMi Force",
            "Thumb Press" : "FitMi Force",

            "Flipping" : "FitMi Flip",
            "Supination" : "FitMi Flip",

            "Bicep Curls" : "FitMi Arm",
            "Rolling" : "FitMi Arm",
            "Shoulder Abduction" : "FitMi Arm",
            "Shoulder Extension" : "FitMi Arm",
            "Wrist Deviation" : "FitMi Arm",
            
            "Finger Twists" : "FitMi Twist",
            "Flyout" : "FitMi Twist",
            "Rotate" : "FitMi Twist",
            "Wrist Flexion" : "FitMi Twist",
            
            "Lift" : "FitMi Lift",

            "Generic movement" : "FitMi Generic",
            "Generic bidirectional movement" : "FitMi Generic",

            "Range of Motion Handle" : "ReCheck ROM",
            "Range of Motion Knob" : "ReCheck ROM",
            "Range of Motion Wrist" : "ReCheck ROM",

            "Isometric Handle" : "ReCheck Isometric",
            "Isometric Knob" : "ReCheck Isometric",
            "Isometric Wrist" : "ReCheck Isometric",

            "Isometric Pinch" : "ReCheck Pinch",
            "Isometric Pinch Left" : "ReCheck Pinch",
            "Isometric Pinch Flexion" : "ReCheck Pinch",
            "Isometric Pinch Extension" : "ReCheck Pinch",
            "Isometric Pinch Left Flexion" : "ReCheck Pinch",
            "Isometric Pinch Left Extension" : "ReCheck Pinch",

            "Touch" : "Touchscreen",

            "Typing" : "Keyboard",
            "Typing (left handed words)" : "Keyboard",
            "Typing (right handed words)" : "Keyboard",

            "Unknown" : "Unknown"
        }

        retrieve_set_category_color_palette = {
            "Shapes" : "#FFEC16",
            "Polygons" : "#fc9003",
            "Texture" : "#f72f02",
            "Weight" : "#9C1AB1",
            "Length" : "#46AF4A",
            "Intro" : "#1093F5",
            "RePlay" : "#000000"
        }

        retrieve_set_category_map = {
            "Shapes" : "Shapes",
            "Solid Shapes" : "Shapes",
            "Polygons" : "Polygons",

            "Handles" : "Texture",
            "Handles (Ro)" : "Texture",
            "Handles (Sq)" : "Texture",

            "Weight" : "Weight",

            "Length" : "Length",
            "Rods" : "Length",

            "Intro: Find" : "Intro",
            "Intro: Discriminate" : "Intro",
        }

        distinguishable_colors_palette = [
            "#0000FF", #Blue
            "#FF0000", #Red
            "#00FF00", #Green
            "#FFD300", #Yellow

            "#7209B7", #Purple
            "#FA8128", #Orange
            "#0F9D58", #Google Green
            "#9E4F46", #Brown

            "#00FFC1", #Cyan
            "#FF1AB9", #Pink

            "#98BF64", #Olive green
            "#C9BB8E", #Hazel wood brown

        ]

        google_color_palette = [
            "#4285F4",  #Google Blue
            "#DB4437",  #Google Red
            "#FBB400",  #Google Yellow
            "#0F9D58",  #Google Green
        ]

        @staticmethod
        def get_distinguishable_color (color_idx):
            true_color_idx = color_idx % len(RePlayExercises.distinguishable_colors_palette)
            return RePlayExercises.distinguishable_colors_palette[true_color_idx]
