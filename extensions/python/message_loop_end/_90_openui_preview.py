from helpers.extension import Extension
from usr.plugins.openui.helpers.current_answer import finish


class OpenUIPreviewEnd(Extension):
    async def execute(self, loop_data=None, **kwargs):
        if self.agent:
            finish(self.agent, loop_data)
