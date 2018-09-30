from PythonClientAPI.game.PointUtils import *
from PythonClientAPI.game.Entities import FriendlyUnit, EnemyUnit, Tile
from PythonClientAPI.game.Enums import Team
from PythonClientAPI.game.World import World
from PythonClientAPI.game.TileUtils import TileUtils
import numpy as np
import random
class PlayerAI:
    def __init__(self):
        ''' Initialize! '''
        self.turn_count = 0             # game turn count
        self.target = None              # target to send unit to!
        self.outbound = True            # is the unit leaving, or returning?
        self.runAway = 2
        self.defend = 3  # how close should an enemy head be in order for us to trigger hide
        self.hide = False
        self.getBackHere = None
        self.firstInbound = False
        self.tempTarget = None
        self.turnMade = False
        self.maxBodyLength = 10
        self.dirSet = False
        self.continueRunningAway = False
        self.inSea = False
        self.prev = None
        self.doublePrev = None
    def do_move(self, world, friendly_unit, enemy_units):
            '''
            This method is called every turn by the game engine.
            Make sure you call friendly_unit.move(target) somewhere here!

            Below, you'll find a very rudimentary strategy to get you started.
            Feel free to use, or delete any part of the provided code - Good luck!

            :param world: world object (more information on the documentation)
                - world: contains information about the game map.
                - world.path: contains various pathfinding helper methods.
                - world.util: contains various tile-finding helper methods.
                - world.fill: contains various flood-filling helper methods.

            :param friendly_unit: FriendlyUnit object
            :param enemy_units: list of EnemyUnit objects
            '''

            # increment turn count
            self.turn_count += 1
            self.doublePrev = self.prev
            self.prev = self.target

            if world.position_to_tile_map[friendly_unit.position].owner is friendly_unit.team and not self.firstInbound:
                self.outbound = True
            if self.turnMade and world.position_to_tile_map[friendly_unit.position].owner is friendly_unit.team:
                self.turnMade = False

            if (len(friendly_unit.body)>=10):
                self.outbound = False
                self.firstInbound = True
            # if unit is dead, stop making moves.
            if friendly_unit.status == 'DISABLED':
                print("Turn {0}: Disabled - skipping move.".format(str(self.turn_count)))
                self.target = None
                self.outbound = True
                return
            # if len(friendly_unit.body)== 0 and world.position_to_tile_map[friendly_unit.position].owner == friendly_unit.team :
            #     self.getBackHere = friendly_unit
            defRet = self.defensive(world, friendly_unit, enemy_units)
            # if defRet == 0: #mal
            if defRet == 2 or (defRet == 0 and self.target is None) : #optimize
                if self.continueRunningAway == False:
                    self.optimizeMain(world,friendly_unit,enemy_units)


            # set next move as the next point in the path to target

            next_move = world.path.get_shortest_path(friendly_unit.position, self.target.position, friendly_unit.snake)[0]
            if (self.doublePrev == next_move):
                moves = [-1, 1]

                for j in moves:
                    tempPoint = tuple(j, 0)
                    tempDest = tuple(np.add(friendly_unit.position, tempPoint));
                    if world.is_within_bounds(tempDest) and not world.is_wall(tempDest):
                        self.target = world.position_to_tile_map[tempDest]
                        break

                for j in moves:
                    tempPoint = tuple(0, j)
                    tempDest = tuple(np.add(friendly_unit.position, tempPoint));
                    if world.is_within_bounds(tempDest) and not world.is_wall(tempDest):
                        self.target = world.position_to_tile_map[tempDest]
                        break
                next_move = world.path.get_shortest_path(friendly_unit.position, self.target.position, friendly_unit.snake)[0]
            # move!
            friendly_unit.move(next_move)
            print("Turn {0}: currently at {1}, making {2} move to {3}.".format(
                str(self.turn_count),
                str(friendly_unit.position),
                'outbound' if self.outbound else 'inbound',
                str(self.target.position)
            ))

    def defensive(self, world, friendly_unit, enemy_units):
        matrix = [[0 for i in range(5)] for j in range(5)]
        for i in range(-2,3):
            for j in range(-2,3):
                if world.is_within_bounds((friendly_unit.position[0]+i,friendly_unit.position[1]+j)):
                    matrix[i+2][j+2]=world.position_to_tile_map[(friendly_unit.position[0]+i,friendly_unit.position[1]+j)]
                else:
                    matrix[i+2][j+2]=None
        min = 100
        temptarget= None
        for i in matrix:
            for j in i:
                if (j is not None and j.body is not None and j.body!=friendly_unit.team):
                    # self.target = j
                    temp = world.path.get_shortest_path_distance(friendly_unit.position,j.position)
                    if temp < min:
                        min = temp
                        temptarget = j

        if temptarget is not None:
            self.target = temptarget
            return 4

        if (self.target is not None and friendly_unit.position == self.target.position):
            # self.outbound = not self.outbound
            # self.target = None
            # if (self.turnMade):
            #     self.outbound = False
            #     self.firstInbound = True
            self.continueRunningAway = False

        if (friendly_unit.position in friendly_unit.territory and self.target is None and
                world.path.get_shortest_path_distance(friendly_unit.position,
                                                      world.util.get_closest_enemy_head_from(friendly_unit.position,
                                                                                             None).position) < self.defend):
            self.outbound = False
            closestHead = world.util.get_closest_enemy_head_from(friendly_unit.position)
            enemy = world.get_unit_by_team(closestHead.head)
            if len(enemy.body) >= self.defend + 1:
                self.target = world.util.get_closest_enemy_body_from(friendly_unit.position)
            else:
                self.target = None
            return 0 #mal
        if (self.target is not None and len(friendly_unit.body) * self.runAway >
                world.path.get_shortest_path_distance(friendly_unit.position,
                                                      world.util.get_closest_enemy_head_from(friendly_unit.position,
                                                                                             None).position)):
            self.outbound = False
            self.target = None
        if (not self.outbound and self.target is None):
            self.target = world.util.get_closest_friendly_territory_from(friendly_unit.position, None)
            self.continueRunningAway = True
            return 1
        else:
            # self.target = world.util.get_closest_capturable_territory_from(friendly_unit.position, None)
            return 2

    def optimizeMain(self, world, friendly_unit, enemy_units):
        if self.outbound:

            if (len(friendly_unit.body) == 0 and not self.dirSet):
                self.getBackHere = friendly_unit
                self.moveAwayFromHeads(world, friendly_unit, enemy_units)
                self.turnMade = False

            else:
                if len(friendly_unit.body)>0:
                    self.dirSet = False
                if (len(friendly_unit.body) == 3 and not self.turnMade):
                    self.makeATurn(world, friendly_unit, enemy_units)
                elif (self.turnMade):
                    if world.is_wall(friendly_unit.position) or friendly_unit.position == self.target.position:
                        self.outbound = False
                        self.firstInbound = True
                else:

                    difference = tuple(np.subtract(friendly_unit.position, self.getBackHere.position))
                    if difference[0] > 0:
                        self.target = world.position_to_tile_map[tuple(np.add(friendly_unit.position, (1, 0)))]
                    elif difference[0] < 0:
                        self.target = world.position_to_tile_map[tuple(np.add(friendly_unit.position, (-1, 0)))]
                    elif difference[1] > 0:
                        self.target = world.position_to_tile_map[tuple(np.add(friendly_unit.position, (0, 1)))]
                    elif difference[1] < 0:
                        self.target = world.position_to_tile_map[tuple(np.add(friendly_unit.position, (0, -1)))]

                    if not world.is_within_bounds(self.target.position) or world.is_wall(self.target.position):
                        if not self.turnMade:
                            self.makeATurn(world, friendly_unit, enemy_units)
                        else:
                            self.outbound = False
                            self.firstInbound = True

        if not self.outbound:

            if self.firstInbound:
                self.target = None
                self.firstInbound = False

                self.target = world.util.get_closest_friendly_territory_from(friendly_unit.position,
                                                                             friendly_unit.snake)
        return


    def makeATurn(self, world, friendly_unit, enemy_units):

        difference = tuple(np.subtract(friendly_unit.position,self.getBackHere.position))
        corners = world.util.get_friendly_territory_corners()
        edges = world.util.get_friendly_territory_edges()

        maxX = 0

        if abs(difference[0]) > abs(difference[1]):
            currentDir = 0
            nextDir = 1
        else:
            currentDir = 1
            nextDir = 0
        newSpot = None
        for i in edges.union(corners):
            if i.position[currentDir] in range(self.getBackHere.position[currentDir]-2,self.getBackHere.position[currentDir]+3):

                if (abs(self.getBackHere.position[nextDir]-i.position[nextDir])>maxX):
                    maxX = abs(self.getBackHere.position[nextDir]-i.position[nextDir])
                    newSpot = i
        if newSpot is None:
            for i in edges.union(corners):
                    if (abs(self.getBackHere.position[nextDir] - i.position[nextDir]) > maxX):
                        maxX = abs(self.getBackHere.position[nextDir] - i.position[nextDir])
                        newSpot = i
        newTup = [0,0]
        newTup[currentDir] = friendly_unit.position[currentDir]
        newTup[nextDir] = newSpot.position[nextDir]
        newTup = tuple(newTup)
        self.target = world.position_to_tile_map[newTup]
        self.turnMade = True
        return
    def moveAwayFromHeads(self,world,friendly_unit,enemy_units):
        self.outbound = True
        goSouth = (friendly_unit.position[0], friendly_unit.position[1] + 1)
        goNorth = (friendly_unit.position[0], friendly_unit.position[1] - 1)
        goEast = (friendly_unit.position[0] + 1, friendly_unit.position[1])
        goWest = (friendly_unit.position[0] - 1, friendly_unit.position[1])
        direction = [goNorth, goWest, goSouth, goEast]
        maxDistance = 0
        finalDir = direction[random.randint(0, 3)]
        # if (friendly_unit.position[0] is 1):
        #     finalDir = direction[random.choice([0, 2, 3])]
        # elif (friendly_unit.position[0] is 28):
        #     finalDir = direction[random.choice([0, 1, 2])]
        # if (friendly_unit.position[1] is 1):
        #     finalDir = direction[random.choice([1, 2, 3])]
        # elif (friendly_unit.position[1] is 28):
        #     finalDir = direction[random.choice([0, 1, 3])]
        # if (friendly_unit.position[0] is 1 and friendly_unit.position[1] is 1):
        #     finalDir = direction[random.choice([2, 3])]
        # elif (friendly_unit.position[0] is 1 and friendly_unit.position[1] is 28):
        #     finalDir = direction[random.choice([0, 3])]
        # elif (friendly_unit.position[0] is 28 and friendly_unit.position[1] is 1):
        #     finalDir = direction[random.choice([1, 2])]
        # elif (friendly_unit.position[0] is 28 and friendly_unit.position[1] is 28):
        #     finalDir = direction[random.choice([0, 1])]
        edges = world.util.get_friendly_territory_edges()

        min = 1000000
        for edge in edges:
            tempmin = world.path.get_shortest_path_distance(friendly_unit.position,edge.position)
            if tempmin < min:
                remember = edge
                min = tempmin
        self.target = remember
        self.dirSet = True

        for dir in direction:
            # print(world.position_to_tile_map[dir].body)
            # print(friendly_unit.uuid)

            if (world.is_within_bounds(dir) and not world.position_to_tile_map[dir].is_wall and
                    world.position_to_tile_map[dir].owner is not friendly_unit.team and
                    dir not in friendly_unit.body):
                distance = world.path.get_shortest_path_distance(dir,
                                                                 world.util.get_closest_enemy_head_from(dir, None).position)
                if (distance > maxDistance):
                    maxDistance = distance
                    finalDir = dir
                    self.target = world.position_to_tile_map[finalDir]
                    # self.dirSet = True


        return