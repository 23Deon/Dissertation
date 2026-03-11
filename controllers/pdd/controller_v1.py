from gridbot.sim.actions import Action


class Controller:
    def act(self, observation):
        return Action.FORWARD