// 허브 화분 아파트 · 구조 시험용 축소 모델 (반 크기)
//
// 물 시험(water_test.scad)이 물길을 봤다면, 이 모형은 탑이 한쪽 무게에 버티는지를 본다.
// 모든 치수가 k 배라 넘어짐과 들림은 실물과 같은 비율로 나온다 (무게와 팔길이가 같이 줄어서).
// 틈은 출력 한계 때문에 꽂이 0.15 mm, 팔과 코어 0.6 mm 로 둔다 (실물 비율보다 조금 헐겁다 = 불리한 쪽).
//
// 구성 (아래부터)
//   받침판: 맨 아래 코어가 소켓에 꽂힌다.
//   맨 아래 층: 코어 + 팔 넷 (매달린 물길 층. 필로티 없음)
//   1층: 코어만. 팔이 없어 위에서 눌러 주는 무게가 적다 = 불리한 쪽
//   2층(맨 위): 코어 + 팔 넷 + 물 추 통. 통마다 물을 따로 채워 한쪽 무게를 만든다.
// 무게: 실물 팔 하나의 짐(물 0.5 L, 바구니, 배지, 식물 약 0.8 kg)은 k³ 배라 반 크기에서 약 100 g = 물 100 mL.
//
// 2026-11-27 첫 시험(필로티 바닥): 코어 이음은 버텼고, 맨 위 두 팔에 물을 채워 사이 각을 약 150° 까지 좁히자 넘어갔다.
// 바닥에 눕힌 팔은 무게가 코어로 가지 않아 추가 되지 못했다. 그래서 받침판으로 바꿨다.
//
// part = "struct_tower"  조립한 모습 (미리보기·틈 검사용)
//        "core" "core_base" "plate" "arm" "tank"  출력 방향 (cross_floor.scad 와 같은 이름)
// openscad -o stl/struct/s05_tank.stl -D 'part="tank"' struct_test.scad

include <cross_floor.scad>

k = 0.5;
part = "struct_tower";

module struct_tower() {
    translate([0, 0, base_lift()]) {
        floor_set(true);
        translate([0, 0, Hf]) core();
        translate([0, 0, 2 * Hf]) {
            floor_set();
            for (a = [0, 90, 180, 270]) rotate(a) tank();
        }
    }
}

if (part == "struct_tower") struct_tower();

echo(str("STRUCT k=", k, " Hf=", Hf, " spig=", spig, " clr=", clr, " plate=", pl_w, " total_h=", base_lift() + 2 * Hf + R));
