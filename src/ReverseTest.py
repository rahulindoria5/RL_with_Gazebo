#!/usr/bin/env python
import rospy
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelState
import numpy as np
import sys, random
import matplotlib.pyplot as plt
import pylab
from keras.layers import Dense
from keras.models import Sequential
from keras.optimizers import Adam
import math
import datetime

# Environment Setting
num_episodes = 10
obstacleRadius = 0.18
agentRadius = 0.18
obsNumber = 10
state_size = 2
action_size = 9
boundaryRadius = 0.85
movingUnit = 0.017
goalPos = [5, 5]
moveObstacles = True


# A2C(Advantage Actor-Critic) agent
class A2CAgent:
    def __init__(self, state_size, action_size):
        self.load_model1 = True
        # self.load_model2 = True
        
        # get size of state and action
        self.state_size = state_size
        self.action_size = action_size
        self.value_size = 1

        # These are hyper parameters for the Policy Gradient
        self.discount_factor = 0.99
        self.actor_lr = 0.00002
        self.critic_lr = 0.00005

        # create model for policy network
        self.actor = self.build_actor()
        self.critic = self.build_critic()

        if self.load_model1:
            # self.actor.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Actor_Rev.h5")
            # self.critic.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Critic_Rev.h5")
            self.actor.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/backup/Actor_Rev_180112.h5")
            self.critic.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/backup/Critic_Rev_180112.h5")

        # if self.load_model2:
        #     self.actor.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Actor_Macro.h5")
        #     self.critic.load_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Critic_Macro.h5")

            
    # approximate policy and value using Neural Network
    # actor: state is input and probability of each action is output of model
    def build_actor(self):
        actor = Sequential()
        actor.add(Dense(128, input_dim=self.state_size, activation='relu', kernel_initializer='glorot_normal'))
        actor.add(Dense(self.action_size, activation='softmax', kernel_initializer='glorot_normal'))
        actor.summary()
        # See note regarding crossentropy in cartpole_reinforce.py
        actor.compile(loss='categorical_crossentropy', optimizer=Adam(lr=self.actor_lr))
        return actor

    # critic: state is input and value of state is output of model
    def build_critic(self):
        critic = Sequential()
        critic.add(Dense(128, input_dim=self.state_size, activation='relu', kernel_initializer='glorot_normal'))
        critic.add(Dense(self.value_size, activation='linear', kernel_initializer='glorot_normal'))
        critic.summary()
        critic.compile(loss="mse", optimizer=Adam(lr=self.critic_lr))
        return critic

    # using the output of policy network, pick action stochastically
    def get_action(self, state):
        policy = self.actor.predict(state, batch_size=1).flatten()
        return policy

    # update policy network every episode
    def train_model(self, state, action, reward, next_state, done):
        target = np.zeros((1, self.value_size))
        advantages = np.zeros((1, self.action_size))

        value = self.critic.predict(state)[0]
        next_value = self.critic.predict(next_state)[0]

        if done:
            advantages[0][action] = reward - value
            target[0][0] = reward
        else:
            advantages[0][action] = reward + self.discount_factor * (next_value) - value
            target[0][0] = reward + self.discount_factor * next_value

        self.actor.fit(state, advantages, epochs=1, verbose=0)
        self.critic.fit(state, target, epochs=1, verbose=0)

def stateGenerator(obsPosition, agtPosition, idx):
    returnSum = []
    if idx != -1:
        returnSum = returnSum + [agtPosition[0] - obsPosition[idx].pose.position.x, agtPosition[1] - obsPosition[idx].pose.position.y]
    else:
        returnSum = returnSum + [agtPosition[0] - obsPosition[0], agtPosition[1] - obsPosition[1]]
    returnSum = np.reshape(returnSum, [1, state_size])
    return returnSum

def rangeFinder(allObsPos, rangeCenter):
    countObs = 0
    rangeObstacle = [[0,0] for _ in range(obsNumber)]
    allObsAgtDistance = [0 for _ in range(obsNumber)]
    for i in range(0, obsNumber):
        allObsAgtDistance[i] = math.sqrt((allObsPos[i].pose.position.x - rangeCenter[0])**2 + (allObsPos[i].pose.position.y - rangeCenter[1])**2)
        if math.sqrt((rangeCenter[0] - allObsPos[i].pose.position.x)**2 + (rangeCenter[1] - allObsPos[i].pose.position.y)**2) < boundaryRadius:
            rangeObstacle[countObs] = allObsPos[i]
            countObs += 1

    index = np.argmin(allObsAgtDistance)
    return [countObs, rangeObstacle, index]

def goalFinder(agtPos):
    goalAngle = 0
    if goalPos[0] == agtPos[0]:
        if goalPos[1] > agtPos[1]:
            goalAngle = 90 * math.pi / 180
        else:
            goalAngle = -90 * math.pi / 180
    else:
        goalAngle = math.atan(1.0*(goalPos[1]-agtPos[1])/(goalPos[0]-agtPos[0]))
    if goalPos[0] < agtPos[0]:
        goalAngle += math.pi
        
    tmpGoal = [0,0]
    tmpGoal[0] = agtPos[0] + boundaryRadius * math.cos(goalAngle)
    tmpGoal[1] = agtPos[1] + boundaryRadius * math.sin(goalAngle)
    return tmpGoal

def takeAction(action):
    xAction = 0
    yAction = 0

    if action == 2:
        action = 7
    elif action == 7:
        action = 2

    if action == 0:
        xAction = movingUnit
    elif action == 1:
        xAction = movingUnit
        yAction = movingUnit
    elif action == 2:
        yAction = movingUnit
    elif action == 3:
        xAction = -movingUnit
        yAction = movingUnit
    elif action == 4:
        xAction = -movingUnit
    elif action == 5:
        xAction = -movingUnit
        yAction = -movingUnit
    elif action == 6:
        yAction = -movingUnit
    elif action == 7:
        xAction = movingUnit
        yAction = -movingUnit 
    elif action == 8:
        xAction = 0
        yAction = 0
        
    return [xAction, yAction]

def main():
    agent = A2CAgent(state_size, action_size)
    # macroAgent = A2CAgent(state_size, action_size)

    obsAngleIdx= 0
    initPosMainRobot = [0, 0]
    rList = []

    # twistMainRobot_pub = rospy.Publisher('simple_create/cmd_vel', Twist, queue_size=10)
    # twistObstRobot_pub = rospy.Publisher('simple_create2/cmd_vel', Twist, queue_size=10)
    
    posObstRobot_pub = []
    posObstRobot_msg = []

    # twistObstRobot_pub = []
    # twistObstRobot_msg = []
    goalPos_pub = rospy.Publisher('gazebo/set_model_state', ModelState, queue_size=10)
    goalPos_msg = ModelState()
    goalPos_msg.model_name = "unit_cylinder_0"
    posMainRobot_pub = rospy.Publisher('gazebo/set_model_state', ModelState, queue_size = 10)
    posMainRobot_msg = ModelState()
    posMainRobot_msg.model_name = "simple_create"
    
    for i in range(0, obsNumber):
        posObstRobot_pub = posObstRobot_pub + [rospy.Publisher('gazebo/set_model_state', ModelState, queue_size = 10)]
        posObstRobot_msg.append(ModelState())
        posObstRobot_msg[i].model_name = "simple_create" + str(i + 2)
        posObstRobot_msg[i].pose.position.x = initPosMainRobot[0] + obstacleRadius + agentRadius + random.randrange(1, goalPos[0])
        posObstRobot_msg[i].pose.position.y = initPosMainRobot[1] + obstacleRadius + agentRadius + random.randrange(1, goalPos[1])
        posObstRobot_msg[i].pose.position.z = 0
    goalPos_msg.pose.position.x = goalPos[0]
    goalPos_msg.pose.position.y = goalPos[1]
    goalPos_msg.pose.position.z = 0
        # twistObstRobot_pub = twistObstRobot_pub + [rospy.Publisher('simple_create' + str(i+2) + '/cmd_vel', Twist, queue_size=10)]
        # twistObstRobot_msg.append(Twist())
    # twistMainRobot_msg = Twist()
    # twistObstRobot_msg = Twist()
    # twistMainRobot_msg.linear.x = 0
    # twistMainRobot_msg.linear.y = 0
    # twistMainRobot_msg.linear.z = 0
    # twistMainRobot_msg.angular.x = 0
    # twistMainRobot_msg.angular.y = 0
    # twistMainRobot_msg.angular.z = 0

    rospy.init_node('circler', anonymous=True)
    rate = rospy.Rate(50) #hz

    for e in range(num_episodes):
        done = False
        reward = 0
        posMainRobot_msg.pose.position.x = initPosMainRobot[0]
        posMainRobot_msg.pose.position.y = initPosMainRobot[1]
        posMainRobot_msg.pose.position.z = 0
        rospy.logwarn("Episode %d Starts!", e)
        rospy.logwarn(datetime.datetime.now().strftime('%H:%M:%S'))
        
        while not done:
            [rangeObsNumber, rangeObsPos, minIndex] = rangeFinder(posObstRobot_msg, initPosMainRobot)

            # macroState = stateGenerator([posObstRobot_msg[minIndex].pose.position.x, posObstRobot_msg[minIndex].pose.position.y], [posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y], -1)
            # macroPolicy = macroAgent.get_action(macroState)
            # rospy.logwarn(macroPolicy)
            tmpAction = []
            for i in range(0, rangeObsNumber):
                state = stateGenerator(rangeObsPos, [posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y], i)
                policyArr = agent.get_action(state)
                if i == 0:
                    tmpAction = (1 - policyArr)
                else:
                    tmpAction = tmpAction * (1 - policyArr)

            # rospy.logwarn(tmpAction)
            if tmpAction != []:
                tmpArgMax = np.argmax(tmpAction)
                for j in range(0,action_size):
                    if tmpAction[j] > 0.97:
                        tmpAction[j] = 1
                    # elif tmpAction[j] > 0.995:
                        # tmpAction[j] = 0.1
                    else:
                        tmpAction[j] = 0

            if rangeObsNumber == 0:
                tmpAction = [1.0/action_size for _ in range(0,action_size)]
            tmpGoalPos = goalFinder([posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y])

            state = stateGenerator(tmpGoalPos, [posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y], -1)
            policyArr = agent.get_action(state)

            # rospy.logwarn(tmpAction)

            if np.mean(tmpAction) == 0:
                # rospy.logwarn("No Action Selected! Random Action")
                # tmpAction[random.randrange(0, action_size)] = 1
                tmpAction[tmpArgMax] = 1

            tmpAction = tmpAction * np.asarray(policyArr)
            # rospy.logwarn(tmpAction)

            # Must be checked - Applying macro action
            # if rangeObsNumber != 0:
                # tmpAction = tmpAction * np.asarray(1 - macroPolicy)
            # rospy.logwarn(macroPolicy)
            tmpAction = tmpAction / np.sum(tmpAction)
            action = np.random.choice(action_size, 1, p = tmpAction)[0]
            # rospy.logwarn(tmpAction)
            # rospy.logwarn(action)
            # action = np.argmax(tmpAction)

            xMove = 0
            yMove = 0
            [xMove, yMove] = takeAction(action)

            posMainRobot_msg.pose.position.x += xMove
            posMainRobot_msg.pose.position.y += yMove

            collisionFlag = 0
            # next_macroState = stateGenerator([posObstRobot_msg[minIndex].pose.position.x, posObstRobot_msg[minIndex].pose.position.y], [posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y], -1)
            initPosMainRobot = [posMainRobot_msg.pose.position.x, posMainRobot_msg.pose.position.y]
            if(math.sqrt((posMainRobot_msg.pose.position.x - goalPos[0])**2 + (posMainRobot_msg.pose.position.y - goalPos[1])**2) <= agentRadius):
                rospy.logwarn("Goal Reached!")
                collisionFlag = 1
                done = True
            for i in range(0, obsNumber):
                if moveObstacles:
                    posObstRobot_msg[i].pose.position.x += random.randrange(-1, 2)/100.0
                    posObstRobot_msg[i].pose.position.y += random.randrange(-1, 2)/100.0
                    # twistObstRobot_msg[i].linear.x = random.randrange(-1, 2)
                    # twistObstRobot_msg[i].angular.z = random.randrange(-1, 2)
                if math.sqrt((posMainRobot_msg.pose.position.x - posObstRobot_msg[i].pose.position.x)**2 + (posMainRobot_msg.pose.position.y - posObstRobot_msg[i].pose.position.y)**2) <= obstacleRadius + agentRadius:
                    rospy.logwarn("Collision!")
                    collisionFlag = -1
                    done = True

            if not done:
                reward = 0
            else:
                if collisionFlag == 1:
                    reward = -1000
                    rList.append(1)
                elif collisionFlag == -1:
                    reward = 1000
                    rList.append(0)
            
            # macroAction = np.random.choice(action_size, 1, p=macroPolicy)
            # macroAgent.train_model(macroState, macroAction, reward, next_macroState, done)
            # macroAgent.train_model(macroState, action, reward, next_macroState, done)
            
            # macroState = next_macroState

            if done:
                initPosMainRobot = [0, 0]
                for i in range(0, obsNumber):
                    posObstRobot_msg[i].pose.position.x = initPosMainRobot[0] + obstacleRadius + agentRadius + random.randrange(1, goalPos[0])
                    posObstRobot_msg[i].pose.position.y = initPosMainRobot[1] + obstacleRadius + agentRadius + random.randrange(1, goalPos[1])
                    posObstRobot_msg[i].pose.position.z = 0
                goalPos_msg.pose.position.x = goalPos[0]
                goalPos_msg.pose.position.y = goalPos[1]
                goalPos_msg.pose.position.z = 0

            goalPos_pub.publish(goalPos_msg)
            posMainRobot_pub.publish(posMainRobot_msg)
            for i in range(0, obsNumber):
                posObstRobot_pub[i].publish(posObstRobot_msg[i])
                # twistObstRobot_pub[i].publish(twistObstRobot_msg[i])

            rate.sleep()
        # if e % 50 == 0:
        #     macroAgent.actor.save_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Actor_Macro.h5")
        #     macroAgent.critic.save_weights("/home/howoongjun/catkin_ws/src/simple_create/src/DataSave/Critic_Macro.h5")
    rospy.logwarn("Percent of successful episodes: %f %%", 100.0 * sum(rList)/num_episodes)

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass