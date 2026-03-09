from gridbot.sim.actions import Action, Heading, turn_left, turn_right

class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading
        if gx > x:
            preferred_heading = Heading.E
        elif gx < x:
            preferred_heading = Heading.W   
        elif gy > y:
            preferred_heading = Heading.S
        elif gy < y:
            preferred_heading = Heading.N
        else:
            return Action.WAIT

        if heading == preferred_heading:
            return Action.FORWARD
        if turn_left(heading) == preferred_heading:
            return Action.TURN_LEFT
        else:
            return Action.TURN_RIGHT