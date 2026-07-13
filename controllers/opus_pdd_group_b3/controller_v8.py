from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        return Action.WAIT
