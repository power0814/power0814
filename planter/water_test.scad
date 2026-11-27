// 허브 화분 아파트 · 물 시험용 축소 모델 (반 크기)
//
// cross_floor.scad 를 그대로 쓰고 축척 k 만 바꾼다. 위치와 크기는 반으로 줄지만,
// 틈(꽂이 0.15 / 0.3 / 0.6), 벽 두께 최소값, 물길 최소 크기(홈통 8 mm, 받침 링 홈통 5 mm, 주둥이 6 mm)는 실물과 같다.
// 그래서 물이 지나는 차례(받이 지붕 → 홈통 → 물받이 → 둑 → 주둥이 → 받침 링 홈통 → 아래층)와
// 마개, 집수조, 밸브가 실물과 같은 방식으로 움직이는지 본다. 흐르는 양(분당 몇 L)은 실물과 다르다.
//
// 구성: 받침판 1, 물길 층 floors 개. 맨 아래 층(코어가 판에 꽂히고 팔 아래에 집수 바닥과 밸브)도 물길 층이다.
// 층마다 코어 1, 팔 4, 물받이 4, 마개 4.
// (처음 판은 받침 발 + 필로티였다: 맨 아래 코어 위에 집수조, 바닥에 눕힌 팔. 2026-11-27 판으로 바꿨다)
//
// part = "test_tower"  조립한 모습 (미리보기·틈 검사용)
//        "core" "core_base" "plate" "arm" "tray" "gate" "basket" "valve_body" "valve_plug"   출력 방향 (cross_floor.scad 와 같은 이름)
// openscad -o stl/test/w05_arm.stl -D 'part="arm"' water_test.scad

include <cross_floor.scad>

k = 0.5;
part = "test_tower";
floors = 2;          // 물길 층 수 (맨 아래 층 포함)

module test_tower() {
    translate([0, 0, base_lift()]) {
        floor_set(true); water_set(true);
        for (n = [1 : floors - 1]) translate([0, 0, n * Hf]) { floor_set(); water_set(); }
    }
}

if (part == "test_tower") test_tower();

echo(str("TEST k=", k, " Hf=", Hf, " arm_D=", D, " core_D=", 2 * Rc, " tray_L=", tr_x[1] - tr_x[0],
         " plate=", pl_w, " valve_from_table=", base_lift() + sump_z, " total_h=", base_lift() + (floors - 1) * Hf + R));
