from anode.plugin.plugin import Plugin


class Netatmo(Plugin):
    def loop(self):
        super(self.__class__, self).loop()
