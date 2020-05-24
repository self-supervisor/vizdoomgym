import gym
from gym import spaces
import vizdoom.vizdoom as vzd
import numpy as np
import os
from typing import List

turn_off_rendering = False
try:
    from gym.envs.classic_control import rendering
except Exception as e:
    print(e)
    turn_off_rendering = True

CONFIGS = [
    ["basic.cfg", 3],  # 0
    ["deadly_corridor.cfg", 7],  # 1
    ["defend_the_center.cfg", 3],  # 2
    ["defend_the_line.cfg", 3],  # 3
    ["health_gathering.cfg", 3],  # 4
    ["my_way_home.cfg", 5],  # 5
    ["predict_position.cfg", 3],  # 6
    ["take_cover.cfg", 2],  # 7
    ["deathmatch.cfg", 20],  # 8
    ["health_gathering_supreme.cfg", 3],  # 9
]


class VizdoomEnv(gym.Env):
    def __init__(self, level, **kwargs):
        """
        Base class for Gym interface for ViZDoom. Child classes are defined in vizdoom_env_definitions.py,
        that contain the level parameter and pass through any kwargs from gym.make()
        :param level: index of level in the CONFIGS list above
        :param kwargs: keyword arguments from gym.make(env_name_string, **kwargs) call. 'depth' will render the
        depth buffer and 'labels' will render the object labels and return it in the observation.
        Note that the observation will be a list with the screen buffer as the first element. If no kwargs are
        provided (or depth=False and labels=False) the observation will be of type np.ndarray.
        """

        # parse keyword arguments
        self.depth = kwargs.get("depth", False)
        self.labels = kwargs.get("labels", False)

        # init game
        self.game = vzd.DoomGame()
        self.game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
        scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")
        self.game.load_config(os.path.join(scenarios_dir, CONFIGS[level][0]))
        self.game.set_window_visible(False)
        self.game.set_depth_buffer_enabled(self.depth)
        self.game.set_labels_buffer_enabled(self.labels)
        self.game.clear_available_game_variables()
        self.game.add_available_game_variable(vzd.GameVariable.POSITION_X)
        self.game.add_available_game_variable(vzd.GameVariable.POSITION_Y)
        self.game.add_available_game_variable(vzd.GameVariable.POSITION_Z)
        self.game.add_available_game_variable(vzd.GameVariable.ANGLE)
        self.game.init()
        self.state = None
        self.viewer = None

        self.action_space = spaces.Discrete(CONFIGS[level][1])

        list_spaces: List[gym.Space] = [
            spaces.Box(
                0,
                255,
                (
                    self.game.get_screen_height(),
                    self.game.get_screen_width(),
                    self.game.get_screen_channels(),
                ),
                dtype=np.uint8,
            )
        ]
        if self.depth:
            list_spaces.append(
                spaces.Box(
                    0,
                    255,
                    (self.game.get_screen_height(), self.game.get_screen_width(),),
                    dtype=np.uint8,
                )
            )
        if self.labels:
            list_spaces.append(
                spaces.Box(
                    0,
                    255,
                    (self.game.get_screen_height(), self.game.get_screen_width(),),
                    dtype=np.uint8,
                )
            )
        if len(list_spaces) == 1:
            self.observation_space = list_spaces[0]
        else:
            self.observation_space = spaces.Tuple(list_spaces)

    def step(self, action):
        # convert action to vizdoom action space (one hot)
        act = np.zeros(self.action_space.n)
        act[action] = 1
        act = np.uint8(act)
        act = act.tolist()

        reward = self.game.make_action(act)
        self.state = self.game.get_state()
        done = self.game.is_episode_finished()
        observation = []
        if not done:
            observation.append(np.transpose(self.state.screen_buffer, (1, 2, 0)))
            if self.depth:
                observation.append(self.state.depth_buffer)
            if self.labels:
                observation.append(self.state.labels_buffer)
            info = {
                "position_x": self.state.game_variables[0],
                "position_y": self.state.game_variables[1],
                "position_z": self.state.game_variables[2],
                "angle": self.state.game_variables[3],
            }
        else:
            # there is no state in the terminal step, so a "zero observation is returned instead"
            if isinstance(self.observation_space, spaces.Box):
                observation.append(np.uint8(np.zeros(self.observation_space.shape)))
            else:
                observation.append(np.uint8(np.zeros(self.observation_space[0].shape)))
            if self.depth:
                observation.append(np.uint8(np.zeros(self.observation_space[1].shape)))
            if self.labels:
                observation.append(np.uint8(np.zeros(self.observation_space[2].shape)))
            info = {
                "position_x": 0.0,
                "position_y": 0.0,
                "position_z": 0.0,
                "angle": 0.0,
            }

        # if there is only one observation, return obs as array to sustain compatibility
        if len(observation) == 1:
            observation = observation[0]

        return observation, reward, done, info

    def reset(self):
        self.game.new_episode()
        self.state = self.game.get_state()
        observation = [np.transpose(self.state.screen_buffer, (1, 2, 0))]
        if self.depth:
            observation.append(self.state.depth_buffer)
        if self.labels:
            observation.append(self.state.labels_buffer)
        if len(observation) == 1:
            observation = observation[0]
        return observation

    def render(self, mode="human"):
        if turn_off_rendering:
            return
        try:
            img = self.game.get_state().screen_buffer
            img = np.transpose(img, [1, 2, 0])

            if self.viewer is None:
                self.viewer = rendering.SimpleImageViewer()
            self.viewer.imshow(img)
        except AttributeError:
            pass

    @staticmethod
    def get_keys_to_action():
        # you can press only one key at a time!
        keys = {
            (): 2,
            (ord("a"),): 0,
            (ord("d"),): 1,
            (ord("w"),): 3,
            (ord("s"),): 4,
            (ord("q"),): 5,
            (ord("e"),): 6,
        }
        return keys
