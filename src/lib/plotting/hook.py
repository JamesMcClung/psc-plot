from typing import Any


class Hook:
    def post_add_hook(self, add_data: Any):
        pass

    def pre_init_fig(self, init_data: Any):
        pass

    def post_init_fig(self, init_data: Any):
        pass

    def pre_update_fig(self, update_data: Any):
        pass

    def post_update_fig(self, update_data: Any):
        pass
