from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    device = LaunchConfiguration('device')
    image_topic = LaunchConfiguration('image_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    use_sim_time = LaunchConfiguration('use_sim_time')
    launch_rviz = LaunchConfiguration('launch_rviz')
    tags_config = PathJoinSubstitution(
        [FindPackageShare('apriltag_ros'), 'cfg', 'tags_36h11.yaml']
    )
    rvizconfig = LaunchConfiguration('rvizconfig')
    default_rvizconfig = PathJoinSubstitution(
        [FindPackageShare('apriltag_ros'), 'cfg', 'apriltag.rviz']
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'device',
            default_value='0',
            description='Camera device passed to camera_ros.',
        ),
        DeclareLaunchArgument(
            'image_topic',
            default_value='/wrist_d405/color',
            description='Input image topic for AprilTag detection.',
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
            'launch_rviz',
            default_value='true',
            description='Launch rviz2 alongside the AprilTag container.',
        ),
        DeclareLaunchArgument(
            'rvizconfig',
            default_value=default_rvizconfig,
            description='Path to the RViz config file.',
        ),
        ComposableNodeContainer(
            name='apriltag_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            composable_node_descriptions=[
                ComposableNode(
                    package='camera_ros',
                    plugin='camera::CameraNode',
                    name='camera',
                    namespace='camera',
                    parameters=[{'camera': device, 'use_sim_time': use_sim_time}],
                    extra_arguments=[{'use_intra_process_comms': True}],
                ),
                ComposableNode(
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
                ),
                ComposableNode(
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
                ),
            ],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rvizconfig],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(launch_rviz),
        ),
    ])
