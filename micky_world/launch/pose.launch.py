import socket

import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessIO
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def _redis_address(plugin_config_path):
    """Redis host/port from the World Plugin parameter file (same values the node reads)."""
    host, port = 'localhost', 6379
    with open(plugin_config_path, 'r') as f:
        params = yaml.safe_load(f) or {}
    for node_params in params.values():
        redis_params = (node_params or {}).get('ros__parameters', {}).get('redis', {})
        host = redis_params.get('host', host)
        port = int(redis_params.get('port', port))
    return host, port


def _redis_is_up(host, port):
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def launch_setup(context, *args, **kwargs):
    plugin_config = LaunchConfiguration('plugin_config').perform(context)
    host, port = _redis_address(plugin_config)

    pose_node = Node(
        package='micky_world',
        executable='pose',
        name='pose',
        parameters=[
            plugin_config,
            {'config_file_name': LaunchConfiguration('config_file_name')}
        ],
    )

    # The pose node writes the poses to Redis as soon as it starts, so the server must already be
    # accepting connections. Reuse one that is running (e.g. a system service on the robot);
    # otherwise start one with this launch, without persistence (poses come from the yaml).
    if _redis_is_up(host, port):
        return [LogInfo(msg=f'Using the Redis server already running at {host}:{port}'), pose_node]

    if host not in ('localhost', '127.0.0.1'):
        return [
            LogInfo(msg=f'Redis at {host}:{port} is not reachable and is not local; not starting one'),
            pose_node,
        ]

    redis_server = ExecuteProcess(
        cmd=['redis-server', '--port', str(port), '--save', '', '--appendonly', 'no'],
        name='redis_server',
        output='screen',
    )

    def start_pose_node_when_ready(event):
        if b'Ready to accept connections' in event.text:
            return [pose_node]
        return None

    return [
        LogInfo(msg=f'Starting a Redis server at {host}:{port}'),
        redis_server,
        RegisterEventHandler(OnProcessIO(target_action=redis_server, on_stdout=start_pose_node_when_ready)),
    ]


def generate_launch_description():

    # Declaração do argumento do Plugin
    plugin_file_arg = DeclareLaunchArgument(
        'plugin_config',
        default_value=PathJoinSubstitution([FindPackageShare('micky_world'), 'config', 'plugin.yaml']),
        description='Path to the World Plugin parameter file'
    )


    poses_file_arg = DeclareLaunchArgument(
        'config_file_name',
        default_value=PathJoinSubstitution([FindPackageShare('micky_world'), 'config', 'poses']),
        description='Path to the poses configuration file'
    )

    return LaunchDescription([
        plugin_file_arg,
        poses_file_arg,
        OpaqueFunction(function=launch_setup),
    ])
