#!/usr/bin/env python3
import pygame
import numpy as np
import rospy
import A1_kinematics
from sensor_msgs.msg import JointState
from unitree_legged_msgs.msg import MotorCmd
from Trajectory_Planner import Trajectory_Planner

# Pygame mostly generated by ChatGPT
command_topics = ["/a1_gazebo/FL_calf_controller/command",
                  "/a1_gazebo/FL_hip_controller/command",
                  "/a1_gazebo/FL_thigh_controller/command",
                  "/a1_gazebo/FR_calf_controller/command",
                  "/a1_gazebo/FR_hip_controller/command",
                  "/a1_gazebo/FR_thigh_controller/command",
                  "/a1_gazebo/RL_calf_controller/command",
                  "/a1_gazebo/RL_hip_controller/command",
                  "/a1_gazebo/RL_thigh_controller/command",
                  "/a1_gazebo/RR_calf_controller/command",
                  "/a1_gazebo/RR_hip_controller/command",
                  "/a1_gazebo/RR_thigh_controller/command"]

Kd = 5
Kp = 300

class PoseControllerUI:
    def __init__(self, width=400, height=300):
        pygame.init()
        pygame.font.init()  # Initialize the font module
        
        self.FONT_SIZE = 24
        self.font = pygame.font.SysFont(None, self.FONT_SIZE)
        
        
        # Screen dimensions and setup
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Pose Controller")

        # Constants
        self.SLIDER_RADIUS = 50
        self.JOYSTICK_RADIUS = 15
        self.CENTER1 = (width*1/5, height/2)
        self.CENTER2 = (width/2, height/2)
        self.CENTER3 = (width*4/5, height/2)


        # Joystick positions
        self.joystick1_pos = self.CENTER1
        self.joystick2_pos = self.CENTER2
        self.joystick3_pos = self.CENTER3
        
        # Active joystick flags
        self.active_joystick1 = False
        self.active_joystick2 = False
        self.active_joystick3 = False
        
        # init ROS and Robots Positions:
        rospy.init_node('pose_publisher_ui', anonymous=True)
        rospy.Subscriber("/a1_gazebo/joint_states", JointState, self.joint_states_callback)
        self.rate = rospy.Rate(25)
        
        self.positions = np.array([0,0,0,0,0,0,
                                   0,0,0,0,0,0])
        self.velocities = np.array([0,0,0,0,0,0,
                                    0,0,0,0,0,0])
        self.goal_pos = np.array([-1.9583591983757351, -0.0007974578255129927, 0.9794434592400876, 
                                  -1.9580158278760527, 0.00048751519737599835, 0.97896869674112, 
                                  -1.968766039552742, 0.0005508150816577739, 0.9651295186701967, 
                                  -1.968942195136563, 0.0002753686771956865, 0.9639652783917043])
        
        self.startup_pos = np.array([-2.6965310400372937, 0.49888734456542494, 1.120544218976467, 
                                    -2.6965319796256715, -0.4970180265271118, 1.1206134112047828, 
                                    -2.696527603682461, 0.4957650374287921, 1.1204999226739023, 
                                    -2.69653004841636, -0.49384031828850805, 1.1206527911125832]) 
        self.base_height = 0.225
        
        self.hip_to_toe_pos = [[-0.0838, 0.225, 0.0],  # FL
                               [0.0838, 0.225, 0.0],  # FR
                               [-0.0838, 0.225, 0.0],  # RL
                               [0.0838, 0.225, 0.0]]  # RR
        
        self.slider_height  = self.height = self.hip_to_toe_pos[0][1]
        
        self.slider_yaw = self.yaw = 0.0  # overall yaw
                
        self.slider_pitch = self.pitch = 0.0  
    
        self.slider_roll = self.roll = 0.0 
         

        self.global_positions = [[0, 0, 0],
                                 [0, 0, 0],
                                 [0, 0, 0],
                                 [0, 0, 0]]
        self.publishers = []
        for topic in command_topics:
            self.publishers.append(rospy.Publisher(topic,MotorCmd, queue_size=0))  # Create Publisher for each Joint
            
            
    def draw_joystick(self, center, position, color, label = "No Label"):
        pygame.draw.circle(self.screen, color, center, self.SLIDER_RADIUS, 2)
        pygame.draw.circle(self.screen, color, position, self.JOYSTICK_RADIUS)
        text_surface = self.font.render(label, True, color)
        text_rect = text_surface.get_rect(center=(center[0], center[1] - self.SLIDER_RADIUS - 20))
        self.screen.blit(text_surface, text_rect)

    def get_joystick_position(self, center, mouse_pos):
        dx = mouse_pos[0] - center[0]
        dy = mouse_pos[1] - center[1]
        distance = np.hypot(dx, dy) 
        if distance > self.SLIDER_RADIUS - self.JOYSTICK_RADIUS:
            angle = np.arctan2(dy, dx) 
            dx = (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS) * np.cos(angle)
            dy = (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS) * np.sin(angle)
        return (center[0] + dx, center[1] + dy)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if np.hypot(event.pos[0] - self.joystick1_pos[0], event.pos[1] - self.joystick1_pos[1]) <= self.JOYSTICK_RADIUS:
                    self.active_joystick1 = True
                elif np.hypot(event.pos[0] - self.joystick2_pos[0], event.pos[1] - self.joystick2_pos[1]) <= self.JOYSTICK_RADIUS:
                    self.active_joystick2 = True
                elif np.hypot(event.pos[0] - self.joystick3_pos[0], event.pos[1] - self.joystick3_pos[1]) <= self.JOYSTICK_RADIUS:
                    self.active_joystick3 = True
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                self.active_joystick1 = False
                self.active_joystick2 = False
                self.active_joystick3 = False
                # reset if slider is let go 
                self.slider_pitch = self.slider_roll = self.slider_yaw = 0.0
                self.slider_height = self.base_height
                self.joystick1_pos = self.CENTER1
                self.joystick2_pos = self.CENTER2
                self.joystick3_pos = self.CENTER3
                
            elif event.type == pygame.MOUSEMOTION:
                if self.active_joystick1:
                    self.joystick1_pos = self.get_joystick_position(self.CENTER1, event.pos)
                    self.slider_roll = ((self.joystick1_pos[0] - self.CENTER1[0]) / (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS))/2

                elif self.active_joystick2:
                    self.joystick2_pos = self.get_joystick_position(self.CENTER2, event.pos)
                    self.slider_yaw = ((self.joystick2_pos[0] - self.CENTER2[0]) / (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS))/2
                    self.slider_height = self.base_height - ((self.joystick2_pos[1] - self.CENTER2[1]) / (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS))/10                 
                elif self.active_joystick3:
                    self.joystick3_pos = self.get_joystick_position(self.CENTER3, event.pos)
                    self.slider_pitch = ((self.joystick3_pos[0] - self.CENTER3[0]) / (self.SLIDER_RADIUS - self.JOYSTICK_RADIUS))/2
                    
        return True

    def run(self):
        running = True
        
        # init MotorCMD Message
        motor_command = MotorCmd()
        motor_command.mode = 10  
        motor_command.Kp = Kp
        motor_command.Kd = Kd 
        
        t = 0
        tp = Trajectory_Planner()
        ## Startup sequence:
        print("Standing up")
        num_steps = 100
        step = (self.goal_pos - self.startup_pos)/num_steps
        
        for i in range(num_steps):
            for i in range(0, len(self.publishers)):
                self.startup_pos[i] += step[i]
                motor_command.q = self.startup_pos[i]
    
                self.publishers[i].publish(motor_command)  
            self.rate.sleep()
        
        while running:
            running = self.handle_events()
            
            # calculate error for each joystick value to current value
            yaw_error = (self.slider_yaw - self.yaw)/10    # dividing by 10 to smoothen the movement
            pitch_error = (self.slider_pitch - self.pitch)/10
            height_error = (self.slider_height -  self.height)/10
            roll_error = (self.slider_roll - self.roll)/10
            
            # ROS CONTROL LOOP
            for legIdx in range(0,4):                

                # add translation
                self.hip_to_toe_pos[legIdx][1] += height_error

                # calculate global positions (base to foot)
                self.global_positions[legIdx] = tp.global_foot_pos(legIdx, self.hip_to_toe_pos[legIdx])
                
                # apply RPY via rotation matrix
                self.global_positions[legIdx] = tp.apply_rpy(self.global_positions[legIdx][0], 
                                                          self.global_positions[legIdx][1], 
                                                          self.global_positions[legIdx][2], 
                                                          roll_error, pitch_error, yaw_error)
                
                # set new local position (hip to foot)
                self.hip_to_toe_pos[legIdx] = tp.local_foot_pos(legIdx,self.global_positions[legIdx])
                
                # get current leg angles from robot
                current_ths = [self.positions[legIdx*3 + 1], 
                               self.positions[legIdx*3 + 2], 
                               self.positions[legIdx*3]]
                
                # calculate closest solution for next position
                goal_ths  = A1_kinematics.calc_correct_thetas([self.hip_to_toe_pos[legIdx][0], 
                                                               self.hip_to_toe_pos[legIdx][1], 
                                                               self.hip_to_toe_pos[legIdx][2]], current_ths, legIdx % 2 == 0)
                
                # set goal angles for corresponding leg
                self.goal_pos[legIdx*3] = goal_ths[2]
                self.goal_pos[legIdx*3 + 1] = goal_ths[0]
                self.goal_pos[legIdx*3 + 2] = goal_ths[1] + np.pi/2
            
            self.yaw += yaw_error
            self.pitch += pitch_error
            self.roll += roll_error
            self.height += height_error
            
            # send joint commands    
            for i in range(0, len(self.publishers)):
                motor_command.q = self.goal_pos[i]
                self.publishers[i].publish(motor_command)  

            t+=1
            t %= 100    
                
            self.screen.fill((255, 255, 255))

            # Draw joysticks
            self.draw_joystick(self.CENTER1, self.joystick1_pos, (0, 0, 255), "Roll/Move X")
            self.draw_joystick(self.CENTER2, self.joystick2_pos, (255, 0, 0), "Yaw/Move Z")
            self.draw_joystick(self.CENTER3, self.joystick3_pos, (0, 255, 0), "Pitch/Move Y")
            
            # Update display
            pygame.display.flip()
            self.rate.sleep()
            
        pygame.quit()
        
    def joint_states_callback(self, data):
        self.positions = data.position
        self.velocities = data.velocity
    
    

if __name__ == "__main__":
    controller = PoseControllerUI()
    controller.run()
