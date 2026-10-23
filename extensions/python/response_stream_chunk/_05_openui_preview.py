from helpers.extension import Extension
from usr.plugins.openui.helpers.current_answer import preview


class OpenUIPreview(Extension):
    async def execute(self, loop_data=None, stream_data=None, **kwargs):
        # Read before the general stream masker, then mask the decoded program
        # ourselves, including incomplete secret prefixes. Never mutate the stream.
        if stream_data:
            preview(self.agent, loop_data, stream_data.get("full"))
