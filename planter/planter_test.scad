// 허브 화분 아파트 · 1 kg 시험 출력 (반투명 PETG)
//
// part = "rings"  벽 두께 고리 넷: 0.8 / 1.2 / 2.0 mm, 1.2 mm 세로 홈
//        "socket" 이음 시험: 받는 쪽 (끝이 그냥 열린 원통)
//        "spigot" 이음 시험: 꽂는 쪽 (끝이 45° 로 좁아져 socket 안으로 들어간다)
//        "arm"    팔 하나: 바깥 끝이 막히고, 옆에 심는 창, 위는 꽂이
// 모두 원통 축을 세워 출력한다 (서포트 없음). 쓸 때는 눕혀 십자의 팔이 된다.
//
// openscad -o arm.stl -D 'part="arm"' planter_test.scad

part = "arm";

D       = 140;     // 원통 바깥 지름
wall    = 1.2;     // 벽 두께
clear   = 0.25;    // 꽂이와 받는 쪽 사이 한쪽 틈
spig    = 20;      // 꽂히는 길이
arm_h   = 270;     // 팔 전체 높이 (꽂이 포함)
cap_t   = 2.0;     // 팔 바깥 끝 막음 두께
win_w   = 70;      // 심는 창 너비
win_z   = [45, 205];  // 창의 아래·위 (뾰족한 지붕 아래까지)
ring_h  = 30;
$fn     = 240;

R  = D / 2;
Rs = R - wall - clear;          // 꽂이 바깥 반지름 = 받는 쪽 안 반지름 − 틈
c  = R - Rs;                     // 45° 경사 구간 높이

// 원통 벽 (열린 양 끝). 꽂이가 있으면 h0 에서 45° 로 좁아져 spig 만큼 더 올라간다.
module shell(h0, w = wall, spigot = false) {
    top = spigot ? h0 + c + spig : h0;
    outer = spigot ? [[0, -1], [R, -1], [R, h0], [Rs, h0 + c], [Rs, top + 1], [0, top + 1]]
                   : [[0, -1], [R, -1], [R, top + 1], [0, top + 1]];
    inner = spigot ? [[0, -2], [R - w, -2], [R - w, h0], [Rs - w, h0 + c], [Rs - w, top + 2], [0, top + 2]]
                   : [[0, -2], [R - w, -2], [R - w, top + 2], [0, top + 2]];
    intersection() {
        difference() {
            rotate_extrude() polygon(outer);
            rotate_extrude() polygon(inner);
        }
        translate([-R - 1, -R - 1, 0]) cube([2 * R + 2, 2 * R + 2, top]);
    }
}

// 겉면 세로 홈 (빛이 갈라지는 모양 시험): 바깥에서 얕은 홈을 판다
module fluted_ring(h, w = wall, n = 60, depth = 0.8) {
    difference() {
        shell(h, w + depth);
        for (i = [0 : n - 1]) rotate(i * 360 / n)
            translate([R, 0, -1]) cylinder(h = h + 2, r = depth * 1.4, $fn = 24);
    }
}

// 심는 창: +x 쪽 벽만 뚫는다. 윗변은 45° 지붕이라 서포트 없이 출력된다.
module window() {
    a = win_z[0];
    b = win_z[1];
    hw = win_w / 2;
    translate([0, 0, 0]) rotate([90, 0, 90])
        linear_extrude(R + 2)
            polygon([[-hw, a], [hw, a], [hw, b], [0, b + hw], [-hw, b]]);
}

module arm() {
    h0 = arm_h - c - spig;
    union() {
        difference() {
            shell(h0, spigot = true);
            window();
        }
        cylinder(h = cap_t, r = R - 0.01);           // 바깥 끝 막음 (출력할 때 바닥)
    }
}

if (part == "rings") {
    walls = [0.8, 1.2, 2.0];
    for (i = [0 : 2]) translate([(i % 2) * (D + 10), floor(i / 2) * (D + 10), 0]) {
        shell(ring_h, walls[i]);
    }
    translate([D + 10, D + 10, 0]) fluted_ring(ring_h, 1.2);
} else if (part == "socket") {
    shell(40);
} else if (part == "spigot") {
    shell(40, spigot = true);
} else if (part == "arm") {
    arm();
}

echo(str("DIMS D=", D, " wall=", wall, " spigot_outer=", 2 * Rs, " socket_inner=", D - 2 * wall,
         " clearance_each_side=", clear, " arm_h=", arm_h));
