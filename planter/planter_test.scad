// 허브 화분 아파트 · 1 kg 시험 출력 (반투명 PETG)
//
// part = "rings"  벽 두께 고리 넷: 0.8 / 1.2 / 2.0 mm, 1.2 mm 세로 홈 (지름은 팔과 같은 140)
// 원통 축을 세워 출력한다 (서포트 없음). 팔, 코어, 쌓기 이음 시험 조각은 cross_floor.scad.
//
// openscad -o stl/rings.stl -D 'part="rings"' planter_test.scad

part = "rings";

D       = 140;     // 원통 바깥 지름
ring_h  = 30;
$fn     = 240;

R = D / 2;

// 원통 벽 (열린 양 끝)
module shell(h, w) {
    intersection() {
        difference() {
            rotate_extrude() polygon([[0, -1], [R, -1], [R, h + 1], [0, h + 1]]);
            rotate_extrude() polygon([[0, -2], [R - w, -2], [R - w, h + 2], [0, h + 2]]);
        }
        translate([-R - 1, -R - 1, 0]) cube([2 * R + 2, 2 * R + 2, h]);
    }
}

// 겉면 세로 홈 (빛이 갈라지는 모양 시험): 바깥에서 얕은 홈을 판다
module fluted_ring(h, w, n = 60, depth = 0.8) {
    difference() {
        shell(h, w + depth);
        for (i = [0 : n - 1]) rotate(i * 360 / n)
            translate([R, 0, -1]) cylinder(h = h + 2, r = depth * 1.4, $fn = 24);
    }
}

if (part == "rings") {
    walls = [0.8, 1.2, 2.0];
    for (i = [0 : 2]) translate([(i % 2) * (D + 10), floor(i / 2) * (D + 10), 0]) shell(ring_h, walls[i]);
    translate([D + 10, D + 10, 0]) fluted_ring(ring_h, 1.2);
}

echo(str("DIMS D=", D, " ring_h=", ring_h));
