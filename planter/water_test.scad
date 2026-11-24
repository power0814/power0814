// 허브 화분 아파트 · 물 시험용 축소 모델 (반 크기)
//
// cross_floor.scad 를 그대로 쓰고 축척 k 만 바꾼다. 위치와 크기는 반으로 줄지만,
// 틈(0.25 / 0.3 / 0.6), 벽 두께 최소값, 물길 최소 크기(홈통 8 mm, 받침 링 홈통 5 mm, 주둥이 6 mm)는 실물과 같다.
// 그래서 물이 지나는 차례(받이 지붕 → 홈통 → 물받이 → 둑 → 주둥이 → 받침 링 홈통 → 아래층)와
// 마개, 집수조, 밸브가 실물과 같은 방식으로 움직이는지 본다. 흐르는 양(분당 몇 L)은 실물과 다르다.
//
// 구성: 받침 발 1, 맨 아래 코어 1 (집수조, 밸브 자리), 밸브 1, 물길 층 2개 (코어 1, 팔 4, 물받이 4, 마개 4 씩)
// 맨 아래 층 팔 네 개 대신 십자 발로 세운다 (물이 닿지 않는 층이라 시험에 필요 없다).
//
// part = "test_tower"  조립한 모습 (미리보기·틈 검사용)
//        "foot"        받침 발
//        "core" "core_base" "arm" "tray" "gate" "valve_body" "valve_plug"   출력 방향 (cross_floor.scad 와 같은 이름)
// openscad -o stl/test/w05_arm.stl -D 'part="arm"' water_test.scad

include <cross_floor.scad>

k = 0.5;
part = "test_tower";
floors = 2;          // 물길 층 수

foot_l = 130;        // 발 팔 길이 (코어 축에서)
foot_w = 16;
foot_t = 4;
sock_h = 6;          // 맨 아래 코어를 끼우는 고리 높이

module foot() {
    rs = Rc + cl_out + 0.3;              // 맨 아래 코어 바닥(받침 링이 바닥까지 내려온다)을 받는 고리 안 반지름
    difference() {
        union() {
            for (a = [0, 90]) rotate(a) translate([-foot_l, -foot_w / 2, 0]) cube([2 * foot_l, foot_w, foot_t]);
            cylinder(h = foot_t + sock_h, r = rs + 2.5);
        }
        translate([0, 0, foot_t]) cylinder(h = sock_h + 1, r = rs);
    }
}

module test_tower() {
    foot();
    translate([0, 0, foot_t + R]) {
        core(-R, true);
        rotate(45) translate([0, 0, sump_z]) { valve_body(); translate([vx, 0, 0]) valve_plug(); }
        for (n = [1 : floors]) translate([0, 0, n * Hf]) { floor_set(); water_set(); }
    }
}

if (part == "test_tower") test_tower();
else if (part == "foot") foot();

echo(str("TEST k=", k, " Hf=", Hf, " arm_D=", D, " core_D=", 2 * Rc, " tray_L=", tr_x[1] - tr_x[0],
         " valve_from_table=", foot_t + R + sump_z, " total_h=", foot_t + R + floors * Hf + R));
