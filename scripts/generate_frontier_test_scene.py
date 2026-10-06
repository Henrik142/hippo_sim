#!/usr/bin/env python3
import random
import re
from pathlib import Path

from ament_index_python.packages import get_package_share_path

world_x = 5.0
world_y = 5.0
wall_thickness = 0.1

num_boxes = 10
min_sidelength = wall_thickness
max_sidelength = 1.0

num_cylinders = 5
min_diameter = min_sidelength
max_diameter = max_sidelength


def format_number(value):
    return f'{value:.6g}'


def get_scene_path():
    source_scene_path = (Path(__file__).resolve().parents[1] /
                         'models/world/frontier_test_scene.sdf')
    if source_scene_path.is_file():
        return source_scene_path
    return (get_package_share_path('hippo_sim') /
            'models/world/frontier_test_scene.sdf')


def update_wall(scene, name, x, y, size_x, size_y):
    model_pattern = re.compile(
        rf'(<model name="{re.escape(name)}">.*?</model>)',
        re.DOTALL,
    )
    match = model_pattern.search(scene)
    if match is None:
        raise ValueError(f'Could not find model [{name}] in scene file')

    model = match.group(1)
    pose_pattern = re.compile(r'(<pose>)([^<]+)(</pose>)')
    pose_match = pose_pattern.search(model)
    if pose_match is None:
        raise ValueError(f'Model [{name}] has no pose')
    pose = pose_match.group(2).split()
    if len(pose) != 6:
        raise ValueError(f'Model [{name}] pose must contain six values')
    new_pose = ' '.join(
        format_number(value)
        for value in (x, y, float(pose[2]), *map(float, pose[3:])))
    model = pose_pattern.sub(f'<pose>{new_pose}</pose>', model, count=1)

    size_pattern = re.compile(r'(<size>)([^<]+)(</size>)')
    size_matches = list(size_pattern.finditer(model))
    if len(size_matches) != 2:
        raise ValueError(
            f'Model [{name}] must have collision and visual box sizes')

    def replace_size(_match):
        size_text = _match.group(2).split()
        if len(size_text) != 3:
            raise ValueError(f'Model [{name}] box size must have three values')
        new_size = ' '.join(
            format_number(value)
            for value in (size_x, size_y, float(size_text[2])))
        return f'<size>{new_size}</size>'

    model = size_pattern.sub(replace_size, model)
    return scene[:match.start()] + model + scene[match.end():]


def remove_existing_obstacles(scene):
    obstacle_pattern = re.compile(
        r'\s*<model name="(?:box|cylinder)_obstacle_[^"]+">.*?</model>',
        re.DOTALL,
    )
    return obstacle_pattern.sub('', scene)


def wall_vertical_dimensions(scene):
    model_pattern = re.compile(
        r'<model name="wall_1">(.*?)</model>',
        re.DOTALL,
    )
    model_match = model_pattern.search(scene)
    if model_match is None:
        raise ValueError('Could not find model [wall_1] in scene file')

    pose_match = re.search(r'<pose>([^<]+)</pose>', model_match.group(1))
    size_match = re.search(r'<size>([^<]+)</size>', model_match.group(1))
    if pose_match is None or size_match is None:
        raise ValueError('Model [wall_1] must have a pose and box size')

    pose = pose_match.group(1).split()
    size = size_match.group(1).split()
    if len(pose) != 6 or len(size) != 3:
        raise ValueError('Model [wall_1] has an invalid pose or box size')
    return float(pose[2]), float(size[2])


def obstacle_model(name, shape, x, y, z, height, size_x, size_y=None):
    pose = ' '.join(format_number(value) for value in (x, y, z, 0, 0, 0))
    if shape == 'box':
        geometry = ('<box><size>'
                    f'{format_number(size_x)} {format_number(size_y)} '
                    f'{format_number(height)}'
                    '</size></box>')
    else:
        geometry = ('<cylinder>'
                    f'<radius>{format_number(size_x / 2)}</radius>'
                    f'<length>{format_number(height)}</length>'
                    '</cylinder>')

    return f'''        <model name="{name}">
            <static>true</static>
            <pose>{pose}</pose>
            <link name="link">
                <collision name="collision">
                    <geometry>{geometry}</geometry>
                </collision>
                <visual name="visual">
                    <geometry>{geometry}</geometry>
                    <material>
                        <ambient>1 1 1 1</ambient>
                        <diffuse>1 1 1 1</diffuse>
                        <specular>1 1 1 1</specular>
                        <pbr>
                            <metal>
                                <metalness>1</metalness>
                                <roughness>0.5</roughness>
                            </metal>
                        </pbr>
                    </material>
                </visual>
            </link>
        </model>'''


def generate_obstacles(scene):
    z, height = wall_vertical_dimensions(scene)
    obstacles = []

    for index in range(num_boxes):
        size_x = random.uniform(min_sidelength, max_sidelength)
        size_y = random.uniform(min_sidelength, max_sidelength)
        x = random.uniform(-world_x / 2 + size_x / 2, world_x / 2 - size_x / 2)
        y = random.uniform(-world_y / 2 + size_y / 2, world_y / 2 - size_y / 2)
        obstacles.append(
            obstacle_model(
                f'box_obstacle_{index + 1}',
                'box',
                x,
                y,
                z,
                height,
                size_x,
                size_y,
            ))

    for index in range(num_cylinders):
        diameter = random.uniform(min_diameter, max_diameter)
        radius = diameter / 2
        x = random.uniform(-world_x / 2 + radius, world_x / 2 - radius)
        y = random.uniform(-world_y / 2 + radius, world_y / 2 - radius)
        obstacles.append(
            obstacle_model(
                f'cylinder_obstacle_{index + 1}',
                'cylinder',
                x,
                y,
                z,
                height,
                diameter,
            ))

    obstacle_block = '\n\n' + '\n\n'.join(obstacles) + '\n\n'
    wall_marker = '        <model name="wall_1">'
    if wall_marker not in scene:
        raise ValueError('Could not find model [wall_1] in scene file')
    return scene.replace(wall_marker, obstacle_block + wall_marker, 1)


def main():
    if world_x <= 0 or world_y <= 0:
        raise ValueError('world_x and world_y must be positive')
    if wall_thickness <= 0 or wall_thickness >= min(world_x, world_y):
        raise ValueError(
            'wall_thickness must be positive and smaller than the world')
    if num_boxes < 0 or num_cylinders < 0:
        raise ValueError('Obstacle counts must not be negative')
    if (min_sidelength <= 0 or min_sidelength > max_sidelength
            or max_sidelength > min(world_x, world_y)):
        raise ValueError('Box side-length bounds are invalid for this world')
    if min_diameter <= 0 or min_diameter > max_diameter:
        raise ValueError('Cylinder diameter bounds are invalid')
    if max_diameter > min(world_x, world_y):
        raise ValueError('Cylinder diameter must fit inside the world')

    scene_path = get_scene_path()
    scene = scene_path.read_text()
    scene = remove_existing_obstacles(scene)

    x_wall_offset = (world_x - wall_thickness) / 2
    y_wall_offset = (world_y - wall_thickness) / 2
    walls = (
        ('wall_1', -x_wall_offset, 0.0, wall_thickness, world_y),
        ('wall_2', 0.0, -y_wall_offset, world_x, wall_thickness),
        ('wall_3', x_wall_offset, 0.0, wall_thickness, world_y),
        ('wall_4', 0.0, y_wall_offset, world_x, wall_thickness),
    )
    for name, x, y, size_x, size_y in walls:
        scene = update_wall(scene, name, x, y, size_x, size_y)

    scene = generate_obstacles(scene)
    scene_path.write_text(scene)
    print(f'Updated wall layout in [{scene_path}]')


if __name__ == '__main__':
    main()
