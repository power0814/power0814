// 허브 화분 아파트 · 구조 시험용 축소 모델 (반 크기)
//
// 물 시험(water_test.scad)이 물길을 봤다면, 이 모형은 탑이 한쪽 무게에 버티는지를 본다.
// 모든 치수가 k 배라 넘어짐과 들림은 실물과 같은 비율로 나온다 (무게와 팔길이가 같이 줄어서).
// 틈은 출력 한계 때문에 꽂이 0.15 mm, 팔과 코어 0.6 mm 로 둔다 (실물 비율보다 조금 헐겁다 = 불리한 쪽).
//
// 구성 (실제 탑과 같은 방식으로 아래부터)
//   맨 아래 층: 맨 아래 코어 + 바닥에 눕힌 팔 넷 (필로티. 받침 발을 쓰지 않는다)
//   1층: 코어만. 팔이 없어 위에서 눌러 주는 무게가 적다 = 불리한 쪽
//   2층(맨 위): 코어 + 팔 넷 + 물 추 통 넷. 통마다 물을 따로 채워 한쪽 무게를 만든다.
// 무게: 실물 팔 하나의 짐(물 0.5 L, 바구니, 배지, 식물 약 0.8 kg)은 k³ 배라 반 크기에서 약 100 g = 물 100 mL.
//
// part = "struct_tower"  조립한 모습 (미리보기·틈 검사용)
//        "core" "core_base" "arm" "tank"  출력 방향 (cross_floor.scad 와 같은 이름)
// openscad -o stl/struct/s05_tank.stl -D 'part="tank"' struct_test.scad

include <cross_floor.scad>

k = 0.5;
part = "struct_tower";

module struct_tower() {
    translate([0, 0, R]) {
        floor_set(true);
        translate([0, 0, Hf]) core();
        translate([0, 0, 2 * Hf]) {
            floor_set();
            for (a = [0, 90, 180, 270]) rotate(a) tank();
        }
    }
}

if (part == "struct_tower") struct_tower();

echo(str("STRUCT k=", k, " Hf=", Hf, " spig=", spig, " clr=", clr, " total_h=", R + 2 * Hf + R + spig * 0));
