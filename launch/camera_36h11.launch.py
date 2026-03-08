import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def _parse_bool(value):
    return value.lower() in ('1', 'true', 'yes', 'on')


def _create_bag_play_process(context, *args, **kwargs):
    cmd = [
        'ros2',
        'bag',
        'play',
        LaunchConfiguration('bag_path').perform(context),
    ]

    if _parse_bool(LaunchConfiguration('repeat_bag').perform(context)):
        cmd.append('-l')

    if _parse_bool(LaunchConfiguration('bag_use_clock').perform(context)):
        cmd.append('--clock')

    return [ExecuteProcess(cmd=cmd, output='screen')]


def generate_launch_description():
    apriltag_share = FindPackageShare('apriltag_ros')
    default_rvizconfig = PathJoinSubstitution(
        [apriltag_share, 'cfg', 'camera_36h11.rviz']
    )
    tags_config = PathJoinSubstitution(
        [apriltag_share, 'cfg', 'tags_36h11.yaml']
    )

    declared_arguments = [
        DeclareLaunchArgument(
            'device',
            default_value='0',
            description='Camera device passed to camera_ros.',
        ),
        DeclareLaunchArgument(
            'image_topic',
            default_value='/wrist_d405/color',
            description='Raw image topic used by the rectifier, AprilTag node, and RViz.',
        ),
        DeclareLaunchArgument(
            'input_compressed_topic',
            default_value='/wrist_d405/color/compressed',
            description='Compressed image topic to decode before AprilTag detection.',
        ),
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='/wrist_d405/camera_info',
            description='Input camera info topic for AprilTag detection.',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use /clock from rosbag or simulation.',
        ),
        DeclareLaunchArgument(
            'play_bag',
            default_value='false',
            description='Replay a rosbag from this launch file.',
        ),
        DeclareLaunchArgument(
            'bag_use_clock',
            default_value=LaunchConfiguration('use_sim_time'),
            description='Add --clock when replaying the rosbag. Defaults to use_sim_time.',
        ),
        DeclareLaunchArgument(
            'repeat_bag',
            default_value='false',
            description='Add -l to replay the rosbag in a loop.',
        ),
        DeclareLaunchArgument(
            'bag_path',
            default_value=os.path.expanduser('~/src/wrist_d405'),
            description='Absolute path to the rosbag to replay.',
        ),
        DeclareLaunchArgument(
            'launch_rviz',
            default_value='true',
            description='Launch rviz2 alongside the AprilTag container.',
        ),
        DeclareLaunchArgument(
            'rvizconfig',
            default_value=default_rvizconfig,
            description='Path to the RViz config file.',
        ),
    ]

    device = LaunchConfiguration('device')
    image_topic = LaunchConfiguration('image_topic')
    input_compressed_topic = LaunchConfiguration('input_compressed_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    use_sim_time = LaunchConfiguration('use_sim_time')
    play_bag = LaunchConfiguration('play_bag')
    launch_rviz = LaunchConfiguration('launch_rviz')
    rvizconfig = LaunchConfiguration('rvizconfig')

    bag_play_process = OpaqueFunction(
        function=_create_bag_play_process,
        condition=IfCondition(play_bag),
    )

    image_decompressor_node = Node(
        package='image_transport',
        executable='republish',
        name='image_decompressor',
        output='screen',
        arguments=['compressed', 'raw'],
        parameters=[{'use_sim_time': use_sim_time}],
        remappings=[
            ('in/compressed', input_compressed_topic),
            ('out', image_topic),
        ],
    )

    camera_node = ComposableNode(
        package='camera_ros',
        plugin='camera::CameraNode',
        name='camera',
        namespace='camera',
        parameters=[{'camera': device, 'use_sim_time': use_sim_time}],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    rectify_node = ComposableNode(
        package='image_proc',
        plugin='image_proc::RectifyNode',
        name='rectify',
        namespace='camera',
        parameters=[{'use_sim_time': use_sim_time}],
        remappings=[
            ('image', image_topic),
            ('camera_info', camera_info_topic),
        ],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    apriltag_node = ComposableNode(
        package='apriltag_ros',
        plugin='AprilTagNode',
        name='apriltag',
        namespace='apriltag',
        parameters=[tags_config, {'use_sim_time': use_sim_time}],
        remappings=[
            ('/apriltag/image_rect', image_topic),
            ('/camera/camera_info', camera_info_topic),
        ],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    apriltag_container = ComposableNodeContainer(
        name='apriltag_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        composable_node_descriptions=[
            camera_node,
            rectify_node,
            apriltag_node,
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rvizconfig],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription(
        declared_arguments
        + [
            bag_play_process,
            image_decompressor_node,
            apriltag_container,
            rviz_node,
        ]
    )
