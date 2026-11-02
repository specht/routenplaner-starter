## Manim Animation Library

from manim import *
import heapq

# Routenplanung – Manim Community Edition
# Alle Szenen spielen in 3D: eine Karte mit Gebäuden, Straßen und leuchtenden
# Routen. Die Kamera neigt sich über die Karte und dreht sich langsam.
#
# Rendern:
#   manim -pqh routenplanung.py Karte3D RoutenplanungTitel GraphenUndKosten UngewichteteSuche PriorityQueue Dijkstra UCSvsGreedy AStar Fazit
# Schnelle Vorschau:
#   manim -pql routenplanung.py Karte3D

BG = "#0D1117"
CYAN = "#79C0FF"
BLUE = "#58A6FF"
PURPLE = "#D2A8FF"
GREEN = "#3FB950"
ORANGE = "#FFA657"
WHITE = "#E6EDF3"
MUTED = "#8B949E"
RED = "#F85149"

# Ein kleiner gewichteter Graph für alle Beispiele.
POS = {
    "S": LEFT * 5.0 + DOWN * 0.2,
    "A": LEFT * 3.1 + UP * 1.25,
    "B": LEFT * 3.0 + DOWN * 1.45,
    "C": LEFT * 0.6 + UP * 1.15,
    "D": RIGHT * 1.6 + DOWN * 0.85,
    "E": RIGHT * 1.45 + UP * 1.45,
    "Z": RIGHT * 4.4 + DOWN * 0.1,
}
EDGES = [
    ("S", "A", 2), ("S", "B", 5), ("A", "B", 1),
    ("A", "C", 4), ("B", "C", 2), ("B", "D", 5),
    ("C", "D", 1), ("C", "E", 4), ("D", "E", 2),
    ("D", "Z", 3), ("E", "Z", 5),
]
NODE_ORDER = list(POS)


def style_scene(scene):
    scene.camera.background_color = BG


def heading(kicker, title, subtitle=None):
    parts = VGroup(
        Text(kicker.upper(), font_size=15, color=CYAN, weight=BOLD),
        Text(title, font_size=37, color=WHITE, weight=BOLD),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
    parts.to_edge(UP, buff=0.35).to_edge(LEFT, buff=0.55)
    if subtitle:
        sub = Text(subtitle, font_size=19, color=MUTED)
        sub.next_to(parts, DOWN, aligned_edge=LEFT, buff=0.18)
        return VGroup(parts, sub)
    return parts


def show_heading(scene, kicker, title, subtitle=None):
    """Der Titel schwebt vor der Kamera, damit er beim Drehen lesbar bleibt."""
    head = heading(kicker, title, subtitle)
    scene.add_fixed_in_frame_mobjects(head)
    scene.play(FadeIn(head, shift=UP * 0.12), run_time=0.9)
    return head


def framed(content, fill="#0B1220", opacity=0.92):
    """Ein dunkler Kasten hinter einem Text, der vor der Kamera schwebt."""
    card = RoundedRectangle(
        corner_radius=0.14,
        width=content.width + 0.55,
        height=content.height + 0.4,
        stroke_color="#243247",
        stroke_width=1,
        fill_color=fill,
        fill_opacity=opacity,
    ).move_to(content)
    return VGroup(card, content)


def note_at(scene, content, edge=DOWN, buff=0.38):
    content.to_edge(edge, buff=buff).to_edge(LEFT, buff=0.55)
    group = framed(content)
    scene.add_fixed_in_frame_mobjects(group)
    scene.play(FadeIn(group, shift=UP * 0.15), run_time=0.8)
    return group


def point(name, height=0.18):
    """Ein Punkt des Graphen in 3D: x und y wie auf der Karte, z nach oben."""
    p = POS[name]
    return np.array([float(p[0]), float(p[1]), height])


def ground_and_grid(size=12.0, depth=8.0):
    """Eine leichte Gitterfläche: wenige Linien statt tausender Segmente.

    NumberPlane sieht ähnlich aus, zerlegt aber jede Linie in hunderte
    Teilstücke. Beim Rendern und bei Create ist das unnötig teuer.
    """
    ground = Square(
        side_length=size,
        stroke_color="#243247",
        stroke_width=1.5,
        fill_color="#101827",
        fill_opacity=1,
    ).set_z(0)
    left, right = -size / 2, size / 2
    bottom, top = -depth / 2, depth / 2
    lines = [
        Line([x, bottom, 0.02], [x, top, 0.02],
             color="#243247", stroke_width=1, stroke_opacity=0.45)
        for x in range(int(left), int(right) + 1)
    ]
    lines += [
        Line([left, y, 0.02], [right, y, 0.02],
             color="#243247", stroke_width=1, stroke_opacity=0.45)
        for y in range(int(bottom), int(top) + 1)
    ]
    return VGroup(ground, VGroup(*lines))


def graph3d(show_weights=True):
    """Die Karte als 3D-Modell: Straßen, Häuser, Knoten und Beschriftungen.

    Die Beschriftungen werden mit add_fixed_orientation_mobjects an die Kamera
    gehängt; sie bleiben dadurch lesbar, auch wenn sich die Kamera dreht.
    """
    roads = VGroup()
    road_caps = VGroup()
    buildings = VGroup()
    nodes = VGroup()
    labels = VGroup()
    weights = VGroup()
    edge_map = {}
    node_map = {}

    for u, v, w in EDGES:
        road = Line3D(point(u), point(v), thickness=0.055, color="#50627D")
        roads.add(road)
        edge_map[frozenset((u, v))] = road
        midpoint = (point(u) + point(v)) / 2
        road_caps.add(
            Cylinder(radius=0.035, height=0.10, color="#7387A5")
            .move_to(midpoint + OUT * 0.06)
        )
        if show_weights:
            direction = np.array([POS[v][0] - POS[u][0], POS[v][1] - POS[u][1], 0.0])
            normal = np.array([-direction[1], direction[0], 0.0])
            if np.linalg.norm(normal) > 0:
                normal /= np.linalg.norm(normal)
            at = midpoint + normal * 0.24 + np.array([0.0, -0.06, 0.30])
            weights.add(Text(str(w), font_size=17, color=ORANGE, weight=BOLD).move_to(at))

    for name in NODE_ORDER:
        height = 0.30 + (len(name) % 3) * 0.12
        buildings.add(
            Prism(
                dimensions=[0.42, 0.42, height],
                fill_color="#1B2A43",
                fill_opacity=0.85,
                stroke_color="#6B7F9E",
                stroke_width=1,
            ).move_to(point(name, height / 2))
        )
        color = GREEN if name == "S" else RED if name == "Z" else CYAN
        node = Sphere(
            center=point(name, 0.48),
            radius=0.16,
            resolution=(10, 6),
            color=color,
            fill_opacity=0.95,
        )
        nodes.add(node)
        node_map[name] = node
        label = Text(name, font_size=22, color=WHITE, weight=BOLD).move_to(
            point(name, 0.95) + np.array([0.0, -0.12, 0.0])
        )
        labels.add(label)

    return {
        "roads": roads,
        "road_caps": road_caps,
        "buildings": buildings,
        "nodes": nodes,
        "labels": labels,
        "weights": weights,
        "edge_map": edge_map,
        "node_map": node_map,
    }


def add_graph(scene, graph, labels=True, weights=True):
    """Beschriftungen an die Kamera hängen; gezeichnet werden sie später.

    Die Mobjecte selbst werden absichtlich nicht sofort hinzugefügt: Sonst
    wären sie schon zu sehen, bevor Create/FadeIn sie einblendet.
    """
    if labels:
        scene.add_fixed_orientation_mobjects(graph["labels"])
    if weights:
        scene.add_fixed_orientation_mobjects(graph["weights"])


def route3d(route, color=GREEN, height=0.55, thickness=0.12):
    return VGroup(
        *[Line3D(point(a, height), point(b, height), thickness=thickness, color=color)
          for a, b in route]
    )


def route_glow(route, color=GREEN, height=0.53):
    glow = VGroup(
        *[Line3D(point(a, height), point(b, height), thickness=0.24, color=color)
          for a, b in route]
    )
    glow.set_fill(color, 0.16)
    return glow


def pulses(scene, points, color=CYAN, run_time=1.2):
    """Ein günstiger Leuchtring statt Indicate auf tausenden 3D-Flächen."""
    rings = VGroup(
        *[Circle(radius=0.24, color=color, stroke_width=3, stroke_opacity=0.9).move_to(p)
          for p in points]
    )
    scene.add(rings)
    scene.play(
        LaggedStart(*[ring.animate.scale(1.9).set_opacity(0) for ring in rings],
                    lag_ratio=0.12),
        run_time=run_time,
    )
    scene.remove(rings)


def shortest_path():
    """Dijkstra auf dem kleinen Graphen – für die Szenen, die den Weg zeigen."""
    adj = {n: [] for n in POS}
    for u, v, w in EDGES:
        adj[u].append((v, w))
        adj[v].append((u, w))
    dist = {n: float("inf") for n in POS}
    prev = {}
    dist["S"] = 0
    heap = [(0, "S")]
    visited_order = []
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue
        visited_order.append(u)
        if u == "Z":
            break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    path = []
    cur = "Z"
    while cur in prev:
        path.append(cur)
        cur = prev[cur]
    path.append("S")
    path.reverse()
    return dist, prev, visited_order, path


def bfs_path():
    """Breitensuche: der Weg mit den wenigsten Kanten."""
    adj = {n: [] for n in POS}
    for u, v, _w in EDGES:
        adj[u].append(v)
        adj[v].append(u)
    parent = {"S": None}
    order = ["S"]
    queue = ["S"]
    while queue:
        u = queue.pop(0)
        for v in adj[u]:
            if v not in parent:
                parent[v] = u
                order.append(v)
                queue.append(v)
    path = []
    cur = "Z"
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return order, path


MAP_FILE = "data/steglitz-zehlendorf.tsv"
ROAD_STYLE = {
    "motorway": ("#D79B32", 4.2),
    "motorway_link": ("#D79B32", 3.2),
    "primary": ("#E4B85A", 3.7),
    "primary_link": ("#E4B85A", 2.8),
    "secondary": ("#AAB5C2", 3.1),
    "secondary_link": ("#AAB5C2", 2.5),
    "tertiary": ("#BBC4CE", 2.6),
    "tertiary_link": ("#BBC4CE", 2.2),
    "residential": ("#D0D6DD", 1.8),
    "living_street": ("#D0D6DD", 1.6),
    "cycleway": ("#C4D0DC", 1.4),
}


def map_roads(path=MAP_FILE):
    """Load a restrained subset of OSM roads and project them onto the scene."""
    ways = []
    bounds = [float("inf"), float("-inf"), float("inf"), float("-inf")]
    with open(path, encoding="utf-8") as data:
        for line in data:
            kind, _oneway, _name, raw_points = line.rstrip("\n").split("\t")
            if kind not in ROAD_STYLE:
                continue
            points = []
            tokens = raw_points.split()
            for index in range(0, len(tokens), 2):
                _node_id, coords = tokens[index:index + 2]
                lon, lat = map(float, coords.split(","))
                points.append((lon, lat))
                bounds[0] = min(bounds[0], lon)
                bounds[1] = max(bounds[1], lon)
                bounds[2] = min(bounds[2], lat)
                bounds[3] = max(bounds[3], lat)
            if len(points) > 1:
                ways.append((kind, points))

    lon_min, lon_max, lat_min, lat_max = bounds
    scale = min(11.2 / (lon_max - lon_min), 6.7 / (lat_max - lat_min))
    y_scale = scale * 1.45

    def project(lon, lat):
        return np.array([
            (lon - (lon_min + lon_max) / 2) * scale,
            (lat - (lat_min + lat_max) / 2) * y_scale,
            0.08,
        ])

    roads = VGroup()
    seen = {kind: 0 for kind in ROAD_STYLE}
    for kind, points in ways:
        seen[kind] += 1
        # Keep the important road hierarchy dense and thin out minor roads.
        if kind in {"residential", "living_street", "cycleway"} and seen[kind] % 12:
            continue
        road = VMobject()
        road.set_points_as_corners([project(lon, lat) for lon, lat in points])
        color, width = ROAD_STYLE[kind]
        road.set_stroke(color=color, width=width, opacity=0.98)
        roads.add(road)
    building_points = []
    for index, (_kind, points) in enumerate(ways[::5]):
        if index % 2:
            lon, lat = points[len(points) // 2]
            building_points.append(project(lon, lat) + np.array([0.11, 0.08, 0.08]))
    return roads, project, building_points


def map_buildings(building_points):
    """Small, quiet 3D blocks add depth without hiding the roads."""
    buildings = VGroup()
    for index, position in enumerate(building_points):
        width = 0.11 + (index % 3) * 0.035
        depth = 0.08 + (index % 2) * 0.025
        height = 0.035 + (index % 4) * 0.012
        building = Prism(
            dimensions=[width, depth, height],
            fill_color="#AEBFA8",
            fill_opacity=0.68,
            stroke_color="#91A88D",
            stroke_width=0.35,
        ).move_to(np.array([position[0], position[1], 0.035]))
        buildings.add(building)
    return buildings


class Karte3D(ThreeDScene):
    """Clean, map-first 3D overview using the bundled OpenStreetMap geometry."""

    def construct(self):
        style_scene(self)
        self.camera.background_color = "#F5F7FA"
        # Start close enough to read the route; the final pull-back provides context.
        # In Manim phi=0 is overhead; a small tilt keeps the building heights visible.
        self.set_camera_orientation(phi=14 * DEGREES, theta=-90 * DEGREES, zoom=1.25)

        header = VGroup(
            Text("ROUTENPLANER", font_size=29, color="#1F2937", weight=BOLD),
            Text("Steglitz-Zehlendorf · route overview",
                 font_size=17, color="#6B7280"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        header.to_corner(UL, buff=0.35)
        self.add_fixed_in_frame_mobjects(header)

        legend = VGroup(
            VGroup(Line(ORIGIN, RIGHT * 0.38, color="#1677FF", stroke_width=6),
                   Text("selected route", font_size=16, color="#1F2937")).arrange(RIGHT, buff=0.12),
            VGroup(Dot(radius=0.075, color="#34A853"),
                   Text("start", font_size=16, color="#1F2937")).arrange(RIGHT, buff=0.12),
            VGroup(Dot(radius=0.075, color="#FB7185"),
                   Text("destination", font_size=16, color="#1F2937")).arrange(RIGHT, buff=0.12),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        legend.to_corner(UR, buff=0.35)
        self.add_fixed_in_frame_mobjects(legend)

        base = Square(
            side_length=14, stroke_width=0, fill_color="#E7EFE4", fill_opacity=1
        ).set_z(0)
        roads, project, building_points = map_roads()
        buildings = map_buildings(building_points)
        phase = Text("1  MAP DATA", font_size=16, color="#6B7280", weight=BOLD)
        phase.to_edge(DOWN, buff=0.25).to_edge(LEFT, buff=0.35)
        self.add_fixed_in_frame_mobjects(phase)
        self.play(FadeIn(base), FadeIn(phase), run_time=0.7)
        self.play(Create(roads), run_time=2.8)
        self.play(FadeIn(buildings), run_time=0.9)

        route_points = [
            project(13.205, 52.415) + OUT * 0.12,
            project(13.245, 52.425) + OUT * 0.12,
            project(13.278, 52.435) + OUT * 0.12,
            project(13.315, 52.445) + OUT * 0.12,
        ]
        route = VMobject()
        route.set_points_as_corners(route_points)
        route.set_stroke("#1677FF", width=8, opacity=1)
        route_glow = VMobject()
        route_glow.set_points_as_corners(route_points)
        route_glow.set_stroke("#1677FF", width=18, opacity=0.16)
        start = Sphere(center=route_points[0] + OUT * 0.12, radius=0.13,
                       resolution=(12, 8), color="#34A853")
        destination = Sphere(center=route_points[-1] + OUT * 0.12, radius=0.13,
                             resolution=(12, 8), color="#FB7185")
        scout = Sphere(center=route_points[0] + OUT * 0.22, radius=0.09,
                       resolution=(10, 6), color="#1677FF")
        start_text = Text("START", font_size=16, color="#166534", weight=BOLD)
        destination_text = Text("DESTINATION", font_size=16, color="#BE123C", weight=BOLD)
        self.add_fixed_orientation_mobjects(start_text, destination_text)
        start_text.move_to(route_points[0] + UP * 0.38)
        destination_text.move_to(route_points[-1] + UP * 0.38)
        destination.set_opacity(0.25)
        destination_text.set_opacity(0.35)
        self.add(scout)
        phase_search = Text("2  SEARCHING FOR A ROUTE", font_size=16,
                            color="#1677FF", weight=BOLD)
        phase_search.to_edge(DOWN, buff=0.25).to_edge(LEFT, buff=0.35)
        self.add_fixed_in_frame_mobjects(phase_search)
        self.play(FadeOut(phase), FadeIn(phase_search), FadeIn(start), FadeIn(start_text),
                  run_time=0.7)
        self.move_camera(
            frame_center=route_points[0],
            zoom=2.15,
            run_time=1.2,
        )
        self.play(
            MoveAlongPath(scout, route, rate_func=there_and_back, run_time=2.4),
            Indicate(start, color="#34A853", scale_factor=1.35),
        )
        phase_found = Text("3  ROUTE FOUND", font_size=16,
                           color="#1677FF", weight=BOLD)
        phase_found.to_edge(DOWN, buff=0.25).to_edge(LEFT, buff=0.35)
        self.add_fixed_in_frame_mobjects(phase_found)
        self.play(
            FadeOut(phase_search),
            FadeIn(phase_found),
            Create(route_glow),
            Create(route),
            FadeIn(destination),
            FadeIn(destination_text),
            run_time=1.5,
        )
        route_steps = []
        for index in range(len(route_points) - 1):
            step = VMobject()
            step.set_points_as_corners(route_points[index:index + 2])
            route_steps.append(step)
        for index, step in enumerate(route_steps):
            self.play(
                MoveAlongPath(scout, step, run_time=0.8, rate_func=smooth),
            )
            self.move_camera(
                frame_center=route_points[index + 1],
                zoom=2.2 + index * 0.12,
                run_time=0.8,
            )
        self.move_camera(
            frame_center=ORIGIN,
            zoom=1.25,
            run_time=1.4,
        )
        self.remove(scout)

        info = framed(
            VGroup(
                Text("WHAT YOU ARE SEEING", font_size=14, color="#1677FF", weight=BOLD),
                Text("1  Streets  →  2  Search  →  3  Best route",
                     font_size=20, color="#1F2937", weight=BOLD),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.08),
            fill="#FFFFFF",
            opacity=0.96,
        )
        info.to_corner(DL, buff=0.35)
        self.add_fixed_in_frame_mobjects(info)
        self.play(FadeIn(info, shift=UP * 0.12), run_time=0.7)
        route_info = Text("Blue = route chosen by the algorithm", font_size=17,
                          color="#374151", weight=BOLD)
        route_info.to_corner(DR, buff=0.28)
        self.add_fixed_in_frame_mobjects(route_info)
        self.play(FadeIn(route_info), run_time=0.5)
        self.wait(3)


class RoutenplanungTitel(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=64 * DEGREES, theta=-52 * DEGREES, zoom=0.95)

        self.add(ground_and_grid(size=14.0, depth=9.0))
        graph = graph3d()
        add_graph(self, graph)
        self.play(
            Create(graph["roads"]),
            FadeIn(graph["road_caps"]),
            FadeIn(graph["buildings"]),
            FadeIn(graph["nodes"]),
            FadeIn(graph["labels"]),
            FadeIn(graph["weights"]),
            run_time=1.8,
        )
        self.begin_ambient_camera_rotation(rate=0.06)

        # Ein dunkler Schleier legt sich über die Karte, der Titel bleibt davor.
        veil = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color=BG,
            fill_opacity=0.60,
            stroke_width=0,
        )
        self.add_fixed_in_frame_mobjects(veil)
        self.play(FadeIn(veil), run_time=0.8)

        kicker = Text("ALGORITHMEN · INFORMATIK", font_size=18, color=CYAN, weight=BOLD)
        title = Text("ROUTEN-\nPLANUNG", font_size=66, color=WHITE, weight=BOLD, line_spacing=0.82)
        subtitle = Text("Wie findet ein Computer den besten Weg?", font_size=24, color=MUTED)
        group = VGroup(kicker, title, subtitle).arrange(DOWN, buff=0.25)
        group.move_to(LEFT * 1.2 + UP * 0.1)
        self.add_fixed_in_frame_mobjects(group)
        self.play(FadeIn(kicker, shift=UP * 0.2))
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle, shift=UP * 0.2))
        self.wait(1.5)

        question = Text("Von S nach Z – welcher Weg ist am besten?",
                        font_size=25, color=GREEN, weight=BOLD)
        question.to_edge(DOWN, buff=0.55)
        self.add_fixed_in_frame_mobjects(question)
        self.play(FadeIn(question))
        self.wait(2)
        self.stop_ambient_camera_rotation()


class GraphenUndKosten(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=60 * DEGREES, theta=-48 * DEGREES, zoom=1.0)
        show_heading(self, "01 · Modell", "Eine Karte wird zum Graphen",
                     "Knoten = Orte  ·  Kanten = Straßen  ·  Gewicht = Kosten")

        self.play(FadeIn(ground_and_grid()), run_time=1.0)
        graph = graph3d()
        add_graph(self, graph)
        self.play(Create(graph["roads"]), run_time=1.5)
        self.play(
            FadeIn(graph["road_caps"]),
            FadeIn(graph["buildings"]),
            FadeIn(graph["nodes"]),
            FadeIn(graph["labels"]),
            FadeIn(graph["weights"]),
            run_time=1.2,
        )

        note = VGroup(
            Text("Route: S → A → B → C → D → Z", font_size=23, color=GREEN, weight=BOLD),
            Text("Gesamtkosten: 2 + 1 + 2 + 1 + 3 = 9", font_size=22, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        note_at(self, note)

        route = [("S", "A"), ("A", "B"), ("B", "C"), ("C", "D"), ("D", "Z")]
        self.play(
            Create(route_glow(route)),
            Create(route3d(route)),
            *[graph["node_map"][name].animate.set_fill(GREEN, 0.95)
              for name in ["S", "A", "B", "C", "D", "Z"]],
            run_time=1.6,
        )
        self.move_camera(phi=66 * DEGREES, theta=-36 * DEGREES, zoom=1.12, run_time=2.5)
        self.wait(2.5)


class UngewichteteSuche(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=62 * DEGREES, theta=-52 * DEGREES, zoom=1.0)
        show_heading(self, "02 · Ohne Kosten", "Wenn jede Kante gleich viel kostet",
                     "BFS (Breitensuche) findet den Weg mit den wenigsten Kanten.")

        self.play(FadeIn(ground_and_grid()), run_time=1.0)
        graph = graph3d(show_weights=False)
        add_graph(self, graph, weights=False)
        self.play(Create(graph["roads"]), run_time=1.3)
        self.play(
            FadeIn(graph["road_caps"]),
            FadeIn(graph["buildings"]),
            FadeIn(graph["nodes"]),
            FadeIn(graph["labels"]),
            run_time=1.0,
        )

        # Die Suche breitet sich wie eine Welle vom Start aus.
        rings = VGroup(
            *[Circle(radius=0.35, color=CYAN, stroke_width=2, stroke_opacity=0.9)
              .move_to(point("S", 0.04)) for _ in range(3)]
        )
        self.add(rings)
        self.play(
            LaggedStart(
                *[ring.animate.scale(3.6).set_opacity(0) for ring in rings],
                lag_ratio=0.35,
            ),
            run_time=2.2,
        )
        self.remove(rings)

        order, path = bfs_path()
        pulses(self, [point(name, 0.50) for name in order], CYAN, run_time=1.6)
        route = list(zip(path[:-1], path[1:]))
        self.play(Create(route_glow(route)), Create(route3d(route)), run_time=1.5)

        note = VGroup(
            Text("BFS", font_size=28, color=GREEN, weight=BOLD),
            Text(f"Weg mit {len(path) - 1} Kanten: {' → '.join(path)}",
                 font_size=22, color=WHITE),
            Text("Gewichtete Straßen? Dann reicht BFS nicht.", font_size=21, color=ORANGE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        note_at(self, note)
        self.move_camera(theta=-40 * DEGREES, zoom=1.08, run_time=2.0)
        self.wait(2.5)


class PriorityQueue(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=62 * DEGREES, theta=-52 * DEGREES, zoom=0.95)
        show_heading(self, "03 · Datenstruktur", "Priority Queue und Heap",
                     "Offene Knoten werden nach Priorität sortiert – kleinster Wert zuerst.")

        self.play(FadeIn(ground_and_grid()), run_time=0.9)

        # Die Warteschlange als HUD links, der Heap als echte 3D-Struktur rechts.
        labels = [
            ("Knoten A", "2", CYAN),
            ("Knoten B", "5", PURPLE),
            ("Knoten C", "7", PURPLE),
            ("Knoten D", "9", PURPLE),
        ]
        cards = VGroup()
        for name, value, color in labels:
            rect = RoundedRectangle(
                corner_radius=0.12, width=4.2, height=0.72,
                stroke_color=color, stroke_width=2,
                fill_color="#111B2E", fill_opacity=0.95,
            )
            left = Text(name, font_size=21, color=WHITE).move_to(rect.get_center() + LEFT * 0.95)
            right = Text("Priorität: " + value, font_size=18, color=color).move_to(rect.get_center() + RIGHT * 0.85)
            cards.add(VGroup(rect, left, right))
        cards.arrange(DOWN, buff=0.16).move_to(LEFT * 4.25 + DOWN * 0.25)
        self.add_fixed_in_frame_mobjects(cards)
        self.play(LaggedStart(*[FadeIn(card, shift=RIGHT * 0.2) for card in cards], lag_ratio=0.15))

        heap_layout = {
            "2": np.array([3.35, 0.0, 2.40]),
            "5": np.array([2.05, 0.0, 1.50]),
            "7": np.array([4.65, 0.0, 1.50]),
            "9": np.array([1.35, 0.0, 0.60]),
            "12": np.array([2.75, 0.0, 0.60]),
        }
        heap_edges = VGroup(
            *[Line3D(heap_layout[a], heap_layout[b], thickness=0.022, color="#52617A")
              for a, b in [("2", "5"), ("2", "7"), ("5", "9"), ("5", "12")]]
        )
        heap_nodes = VGroup()
        heap_labels = VGroup()
        for value, at in heap_layout.items():
            color = GREEN if value == "2" else PURPLE
            heap_nodes.add(Sphere(center=at, radius=0.27, resolution=(10, 6),
                                  color=color, fill_opacity=0.30))
            heap_labels.add(Text(value, font_size=21, color=WHITE, weight=BOLD)
                            .move_to(at + np.array([0.0, -0.30, 0.0])))
        heap_title = Text("MIN-HEAP", font_size=24, color=CYAN, weight=BOLD)
        heap_title.move_to(np.array([3.35, 0.0, 3.10]))
        self.add_fixed_orientation_mobjects(heap_labels, heap_title)
        self.play(
            Create(heap_edges),
            LaggedStart(*[FadeIn(node, scale=0.6) for node in heap_nodes], lag_ratio=0.12),
            FadeIn(heap_labels),
            FadeIn(heap_title),
            run_time=1.4,
        )

        # Das kleinste Element wird entnommen: Karte und Wurzel leuchten auf.
        root_ring = Circle(radius=0.34, color=GREEN, stroke_width=3,
                           stroke_opacity=0.9).move_to(heap_layout["2"])
        self.add(root_ring)
        self.play(
            root_ring.animate.scale(1.9).set_opacity(0),
            heap_nodes[0].animate.set_fill(GREEN, 0.85),
            cards[0].animate.set_opacity(0.35),
            run_time=0.9,
        )
        self.remove(root_ring)
        self.play(
            cards[0].animate.shift(LEFT * 0.6).set_opacity(0),
            cards[1:].animate.shift(UP * 0.88),
            run_time=0.8,
        )
        next_ring = Circle(radius=0.34, color=GREEN, stroke_width=3,
                           stroke_opacity=0.9).move_to(heap_layout["5"])
        self.add(next_ring)
        self.play(
            next_ring.animate.scale(1.8).set_opacity(0),
            heap_nodes[1].animate.set_fill(GREEN, 0.85),
            run_time=0.8,
        )
        self.remove(next_ring)

        explanation = Text("Ein Heap macht Einfügen und Entnehmen effizient.",
                           font_size=20, color=MUTED)
        explanation.to_edge(DOWN, buff=0.45)
        self.add_fixed_in_frame_mobjects(explanation)
        self.play(FadeIn(explanation))
        self.begin_ambient_camera_rotation(rate=0.08)
        self.wait(3)
        self.stop_ambient_camera_rotation()


class Dijkstra(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=62 * DEGREES, theta=-50 * DEGREES, zoom=1.0)
        show_heading(self, "04 · Kürzeste gewichtete Route", "Dijkstra / Uniform Cost Search",
                     "Priorität = bisher bekannte Distanz g(n). Alle Kantengewichte müssen nichtnegativ sein.")

        self.play(FadeIn(ground_and_grid()), run_time=1.0)
        graph = graph3d()
        add_graph(self, graph)
        self.play(Create(graph["roads"]), run_time=1.4)
        self.play(
            FadeIn(graph["road_caps"]),
            FadeIn(graph["buildings"]),
            FadeIn(graph["nodes"]),
            FadeIn(graph["labels"]),
            FadeIn(graph["weights"]),
            run_time=1.1,
        )

        # Die Distanzen als HUD oben rechts.
        panel = RoundedRectangle(
            corner_radius=0.15, width=3.0, height=3.4,
            stroke_color="#34445F", fill_color="#101827", fill_opacity=0.96,
        ).to_corner(UR, buff=0.35).shift(DOWN * 1.55)
        panel_title = Text("DISTANZEN g(n)", font_size=19, color=CYAN, weight=BOLD)
        panel_title.move_to(panel.get_top() + DOWN * 0.35)
        dist_text = Text("S: 0\nA: ∞\nB: ∞\nC: ∞\nD: ∞\nE: ∞\nZ: ∞",
                         font_size=18, color=WHITE, line_spacing=0.55)
        dist_text.move_to(panel.get_center() + DOWN * 0.15)
        self.add_fixed_in_frame_mobjects(panel, panel_title, dist_text)
        self.play(FadeIn(panel), FadeIn(panel_title), FadeIn(dist_text))

        dist, _prev, visited_order, path = shortest_path()
        for node in visited_order:
            shown = "\n".join(
                f"{n}: {dist[n] if dist[n] != float('inf') else '∞'}"
                for n in ["S", "A", "B", "C", "D", "E", "Z"]
            )
            new_text = Text(shown, font_size=18, color=WHITE, line_spacing=0.55)
            new_text.move_to(dist_text)
            beam = Line3D(point(node, 0.55), point(node, 1.05),
                          thickness=0.012, color=ORANGE)
            self.play(
                graph["node_map"][node].animate.set_fill(ORANGE, 0.95),
                Create(beam),
                Transform(dist_text, new_text),
                run_time=0.38,
            )
            self.play(FadeOut(beam), run_time=0.12)

        route = list(zip(path[:-1], path[1:]))
        self.play(
            Create(route_glow(route)),
            Create(route3d(route)),
            *[graph["node_map"][name].animate.set_fill(GREEN, 0.95) for name in path],
            run_time=1.4,
        )
        result = Text("Kürzeste Kosten: 9", font_size=22, color=GREEN, weight=BOLD)
        result.to_edge(DOWN, buff=0.38)
        self.add_fixed_in_frame_mobjects(result)
        self.play(FadeIn(result))
        self.move_camera(theta=-38 * DEGREES, zoom=1.1, run_time=2.2)
        self.wait(2.5)


class UCSvsGreedy(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=62 * DEGREES, theta=-50 * DEGREES, zoom=0.95)
        show_heading(self, "05 · Die Heuristik", "UCS vs. Greedy Best-First",
                     "Greedy schaut auf die geschätzte Restdistanz h(n) zum Ziel.")

        self.play(FadeIn(ground_and_grid()), run_time=0.9)

        def panel(width, height, color, center):
            slab = Prism(
                dimensions=[width, 0.10, height],
                fill_color="#101827", fill_opacity=0.94,
                stroke_color=color, stroke_width=1.4,
            ).move_to(center)
            return slab

        left_at = np.array([-2.9, 0.0, 1.55])
        right_at = np.array([2.9, 0.0, 1.55])
        left = panel(5.2, 2.9, CYAN, left_at)
        right = panel(5.2, 2.9, PURPLE, right_at)

        left_content = VGroup(
            Text("UCS / Dijkstra", font_size=27, color=CYAN, weight=BOLD),
            Text("Priorität = g(n)", color=WHITE, font_size=30),
            Text("Bisherige Wegkosten", font_size=21, color=MUTED),
            Text("Optimal bei nichtnegativen Kosten", font_size=18, color=GREEN),
        ).arrange(DOWN, buff=0.25).move_to(left_at + np.array([0.0, -0.16, 0.0]))
        right_content = VGroup(
            Text("Greedy Best-First", font_size=26, color=PURPLE, weight=BOLD),
            Text("Priorität = h(n)", color=WHITE, font_size=30),
            Text("Geschätzte Entfernung zum Ziel", font_size=20, color=MUTED),
            Text("Kann einen Umweg wählen", font_size=18, color=ORANGE),
        ).arrange(DOWN, buff=0.25).move_to(right_at + np.array([0.0, -0.16, 0.0]))
        versus = Text("VS", font_size=32, color=MUTED, weight=BOLD)
        versus.move_to(np.array([0.0, -0.16, 1.55]))

        self.add_fixed_orientation_mobjects(left_content, right_content, versus)
        self.play(FadeIn(left, shift=RIGHT * 0.3), FadeIn(right, shift=LEFT * 0.3), run_time=1.2)
        self.play(FadeIn(left_content), FadeIn(right_content), FadeIn(versus), run_time=1.0)

        note = Text("Greedy wirkt zielgerichtet – garantiert aber nicht den kürzesten Weg.",
                    font_size=21, color=WHITE)
        note_at(self, note, buff=0.42)
        self.move_camera(phi=66 * DEGREES, theta=-38 * DEGREES, zoom=1.02, run_time=2.4)
        self.wait(2.5)


class AStar(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=62 * DEGREES, theta=-50 * DEGREES, zoom=0.95)
        show_heading(self, "06 · Kombination", "A* verbindet Kosten und Heuristik",
                     "A* bewertet einen Knoten mit f(n) = g(n) + h(n).")

        formula = Text("f(n) = g(n) + h(n)", font_size=46, color=WHITE, weight=BOLD)
        formula.move_to(UP * 2.75)
        self.add_fixed_in_frame_mobjects(formula)
        self.play(Write(formula))

        self.play(FadeIn(ground_and_grid()), run_time=0.9)

        def panel(width, height, color, center):
            return Prism(
                dimensions=[width, 0.10, height],
                fill_color="#101827", fill_opacity=0.94,
                stroke_color=color, stroke_width=1.4,
            ).move_to(center)

        g_at = np.array([-2.4, 0.0, 1.35])
        h_at = np.array([2.4, 0.0, 1.35])
        g_box = panel(3.1, 1.3, GREEN, g_at)
        h_box = panel(3.1, 1.3, PURPLE, h_at)
        g_text = VGroup(
            Text("g(n)", font_size=28, color=GREEN, weight=BOLD),
            Text("Kosten bis hierher", font_size=19, color=WHITE),
        ).arrange(DOWN, buff=0.12).move_to(g_at + np.array([0.0, -0.16, 0.0]))
        h_text = VGroup(
            Text("h(n)", font_size=28, color=PURPLE, weight=BOLD),
            Text("geschätzte Restkosten", font_size=19, color=WHITE),
        ).arrange(DOWN, buff=0.12).move_to(h_at + np.array([0.0, -0.16, 0.0]))
        plus = Text("+", font_size=42, color=WHITE).move_to(np.array([0.0, -0.16, 1.35]))

        self.add_fixed_orientation_mobjects(g_text, h_text, plus)
        self.play(FadeIn(g_box), FadeIn(h_box), run_time=1.0)
        self.play(FadeIn(g_text), FadeIn(h_text), FadeIn(plus), run_time=0.8)

        # g und h als Pfeile: zusammen ergeben sie f.
        base = np.array([-2.1, 0.9, 0.25])
        g_end = base + np.array([2.2, 0.0, 0.0])
        h_end = g_end + np.array([1.1, 0.0, 0.0])
        f_base = base + np.array([0.0, 0.0, 0.95])
        f_end = f_base + np.array([3.3, 0.0, 0.0])
        g_arrow = Arrow3D(base, g_end, thickness=0.045, color=GREEN)
        h_arrow = Arrow3D(g_end, h_end, thickness=0.045, color=PURPLE)
        f_arrow = Arrow3D(f_base, f_end, thickness=0.032, color=CYAN)
        arrow_labels = VGroup(
            Text("g(n)", font_size=20, color=GREEN, weight=BOLD)
            .move_to((base + g_end) / 2 + np.array([0.0, -0.1, 0.32])),
            Text("h(n)", font_size=20, color=PURPLE, weight=BOLD)
            .move_to((g_end + h_end) / 2 + np.array([0.0, -0.1, 0.32])),
            Text("f(n)", font_size=20, color=CYAN, weight=BOLD)
            .move_to((f_base + f_end) / 2 + np.array([0.0, -0.1, 0.32])),
        )
        self.add_fixed_orientation_mobjects(arrow_labels)
        self.play(Create(g_arrow), Create(h_arrow), FadeIn(arrow_labels[0]), FadeIn(arrow_labels[1]), run_time=1.2)
        self.play(Create(f_arrow), FadeIn(arrow_labels[2]), run_time=0.9)

        conclusion = VGroup(
            Text("A* sucht zielgerichtet und berücksichtigt trotzdem die bisherigen Kosten.",
                 font_size=22, color=WHITE),
            Text("Bei zulässiger Heuristik (sie überschätzt nie) kann A* optimal sein.",
                 font_size=20, color=GREEN),
        ).arrange(DOWN, buff=0.25)
        note_at(self, conclusion, buff=0.35)
        self.move_camera(theta=-38 * DEGREES, zoom=1.04, run_time=2.2)
        self.wait(2.5)


class Fazit(ThreeDScene):
    def construct(self):
        style_scene(self)
        self.set_camera_orientation(phi=64 * DEGREES, theta=-50 * DEGREES, zoom=0.92)

        title = Text("WELCHER ALGORITHMUS?", font_size=39, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.55)
        self.add_fixed_in_frame_mobjects(title)
        self.play(Write(title))

        self.play(FadeIn(ground_and_grid()), run_time=0.9)

        rows = [
            ("BFS", "wenigste Kanten", CYAN),
            ("Dijkstra / UCS", "günstigste Kosten", GREEN),
            ("Greedy", "nur h(n)", ORANGE),
            ("A*", "g(n) + h(n)", PURPLE),
        ]
        cards = VGroup()
        texts = VGroup()
        for i, (name, desc, color) in enumerate(rows):
            at = np.array([-3.55 + i * 2.35, -0.35 + i * 0.16, 0.75 + i * 0.42])
            card = Prism(
                dimensions=[2.15, 0.10, 1.15],
                fill_color="#101827", fill_opacity=0.94,
                stroke_color=color, stroke_width=1.4,
            ).move_to(at)
            text = VGroup(
                Text(f"0{i + 1}", font_size=14, color=color, weight=BOLD),
                Text(name, font_size=18, color=color, weight=BOLD),
                Text(desc, font_size=14, color=WHITE),
            ).arrange(DOWN, buff=0.10).move_to(at + np.array([0.0, -0.16, 0.0]))
            cards.add(card)
            texts.add(text)

        self.add_fixed_orientation_mobjects(texts)
        self.begin_ambient_camera_rotation(rate=0.06)
        self.play(
            LaggedStart(*[FadeIn(card, shift=UP * 0.3) for card in cards], lag_ratio=0.18),
            run_time=1.6,
        )
        self.play(LaggedStart(*[FadeIn(text, shift=UP * 0.15) for text in texts], lag_ratio=0.18),
                  run_time=1.2)

        final = Text("Die beste Route hängt davon ab, was wir optimieren.",
                     font_size=23, color=CYAN, weight=BOLD).to_edge(DOWN, buff=0.5)
        self.add_fixed_in_frame_mobjects(final)
        self.play(FadeIn(final))
        self.wait(3)

        thanks = Text("DANKE!", font_size=54, color=GREEN, weight=BOLD)
        self.add_fixed_in_frame_mobjects(thanks)
        self.play(
            FadeOut(VGroup(title, final, cards, texts), shift=UP * 0.2),
            FadeIn(thanks, scale=0.8),
            run_time=1.4,
        )
        self.wait(2)
        self.stop_ambient_camera_rotation()
