from direct.actor.Actor import Actor

class CharacterAnimationController:
    def __init__(self, model_path: str, anims: dict):
        """
        Manages animations for a character.
        :param model_path: Path to the character model file.
        :param anims: A dictionary mapping animation names to animation file paths.
                      Example: {"walk": "path/to/walk.egg", "idle": "path/to/idle.egg"}
        """
        try:
            self.actor = Actor(model_path, anims)
            self.actor.set_scale(0.3)
            self.current_anim = None
        except Exception as e:
            print(f"Failed to load actor: {e}")
            self.actor = None

    def get_actor(self) -> Actor:
        return self.actor

    def play(self, anim_name: str, loop: bool = True):
        """
        Plays a specific animation. If the animation is already playing, it does nothing.
        :param anim_name: The name of the animation to play (must be a key in the `anims` dict).
        :param loop: Whether the animation should loop.
        """
        if not self.actor or self.current_anim == anim_name:
            return

        if self.actor.get_anim_control(anim_name):
            if loop:
                self.actor.loop(anim_name)
            else:
                self.actor.play(anim_name)
            self.current_anim = anim_name
        else:
            print(f"Warning: Animation '{anim_name}' not found for actor.")

    def stop(self):
        """Stops all animations."""
        if self.actor:
            self.actor.stop()
            self.current_anim = None

    def cleanup(self):
        """Removes the actor from the scene."""
        if self.actor:
            self.actor.cleanup()
            self.actor.removeNode()
