// 허브 화분 아파트 · 십자 층: 코어 기둥 + 원통 네 개
//
// 쓰는 좌표: z 위, 코어 축 = z 축. 원통(팔) 넷이 코어에서 +x, +y, −x, −y 로 뻗는다.
// - 코어: 세로 원통 마디. 층마다 하나, 위 끝 꽂이로 쌓는다. 팔 위쪽 높이에 45° 걸이 턱(링)이 돈다.
// - 팔: 가로 원통. 바깥 끝은 막혔고, 코어 쪽 끝은 이웃 팔과 45° 대각선 면으로 맞닿는다.
//   위쪽 벽이 코어 쪽으로 이어진 갈고리가 걸이 턱에 위에서 걸린다 (프렌치 클리트).
//   원통이 처지려는 힘은 갈고리를 턱 쪽으로 더 물리게 하고, 들어 올리면 빠진다.
//   팔 아래 안쪽 끝의 발꿈치가 코어의 받침 링을 민다. 갈고리(당김)와 발꿈치(누름)가 짝힘이 되어 처짐을 받는다.
//   두 링 모두 코어 밖으로 cl_out 만 나오고 팔은 그보다 바깥에서 끝나므로, 팔을 위에서 곧장 내려 끼운다.
//
// part = "floor"     맨 아래 층을 조립한 모습, 팔이 바닥에 놓인다 (미리보기용)
//        "floor_mid" 가운데 층 하나, 팔 축 z = 0 (미리보기에서 쌓을 때 쓴다)
//        "tower"     맨 아래 층 + 둘째 층 (미리보기용)
//        "arm"     팔 하나, 출력 방향 (축을 세우고 코어 쪽 끝이 위)
//        "core"    코어 마디 하나, 출력 방향
//        "core_base" 맨 아래 코어 마디: 바닥이 팔 아래 면과 같은 높이라, 맨 아래 층은 팔이 바닥에 놓인다
//        "core_joint" 쌓기 이음 시험 조각 둘 (코어 아래 끝 / 위 끝 꽂이)
// openscad -o stl/arm.stl -D 'part="arm"' cross_floor.scad

part = "floor";

// 크기
D      = 140;    // 팔 원통 바깥 지름
w      = 1.6;    // 팔 벽
reach  = 320;    // 코어 축에서 팔 바깥 끝까지 (십자 폭 = 2 × reach)
cap    = 2.0;    // 팔 바깥 끝 막음
mt     = 1.6;    // 대각선 면 판 두께
Rc     = 45;     // 코어 바깥 반지름
wc     = 2.5;    // 코어 벽
Hf     = 270;    // 층 간격 (팔 축에서 다음 층 팔 축까지). 7 층이면 맨 위 팔 윗면이 바닥에서 R + 6Hf + R = 1760
gapc   = 0.6;    // 팔과 코어 사이 틈
mgap   = 0.3;    // 이웃 팔과 대각선 면 사이 틈 (한쪽)
// 걸이 (프렌치 클리트)
cl_z   = 56;     // 걸이 턱 꼭대기 높이 (팔 축 = 0 기준). 높을수록 발꿈치와의 팔길이가 길어진다
cl_out = 7;      // 턱이 코어 밖으로 나온 거리
hook_w = 50;     // 갈고리와 발꿈치 너비 (코어 쪽 끝에서 잰 현)
// 받침 (발꿈치)
heel_z = [-68, -54];  // 받침 링과 발꿈치가 맞닿는 높이 범위 (낮을수록 좋다. 팔 아래 벽 안쪽이 −68.4)
heel_l = 8;      // 발꿈치가 팔 끝에서 바깥으로 차지하는 길이
// 심는 창 (팔 위쪽)
win    = [140, 290];  // 창이 놓이는 x 범위 (코어 축 기준)
win_w  = 64;
// 코어 쌓기 꽂이
// 쌓기
twist  = 0;      // 층마다 돌리는 각도. 0 이면 팔이 위아래로 한 줄로 선다 (45 면 엇갈림)
spig   = 18;
clr    = 0.25;
ch     = 1.5;    // 코어 바닥 속 모따기. 아래 마디 어깨(45°)에 이 면으로 앉는다. 남는 이음 줄눈 = wc − ch
$fn    = 160;

R = D / 2;

// ---------- 팔 (쓰는 좌표, +x 쪽) ----------
module arm_solid(r) {        // 반지름 r 원통을 코어 바깥 ~ reach 까지
    rotate([0, 90, 0]) cylinder(h = reach, r = r);
}
module sector() {            // 이 팔의 몫: x ≥ |y| + 틈 (대각선 면 안쪽)
    g = mgap * sqrt(2);
    linear_extrude(height = 4 * R, center = true)
        polygon([[g, 0], [reach + 10, reach + 10 - g], [reach + 10, -reach - 10 + g]]);
}
module core_clear(extra = 0) {
    cylinder(h = 4 * R, r = Rc + cl_out + gapc + extra, center = true);
}
module window_cut() {        // 위쪽 벽의 심는 창. 코어 쪽 끝은 45° (출력할 때 위로 뾰족)
    a = win[0];
    b = win[1];
    hw = win_w / 2;
    translate([0, 0, R - 2 * w]) linear_extrude(height = 3 * w)
        polygon([[a + hw, -hw], [b, -hw], [b, hw], [a + hw, hw], [a, 0]]);
}
module arm() {
    difference() {
        intersection() {
            union() {
                difference() {                      // 원통 벽
                    arm_solid(R);
                    translate([-1, 0, 0]) rotate([0, 90, 0]) cylinder(h = reach - cap + 1, r = R - w);
                }
                // 대각선 면 판 두 장: x = |y| 면에서 안쪽으로 mt 두께
                for (s = [-1, 1]) intersection() {
                    arm_solid(R);
                    linear_extrude(height = 4 * R, center = true)
                        translate([mgap * sqrt(2), 0])
                        polygon([[0, 0], [reach, s * reach], [reach + mt * sqrt(2), s * reach],
                                 [mt * sqrt(2), 0]]);   // 틈 안쪽 면에서 이 팔 쪽(+x)으로 mt 두께
                }
            }
            sector();
        }
        core_clear();
        window_cut();
    }
    hook();
    heel();
}
// 갈고리: 팔 위쪽 벽에서 코어 쪽으로 넘어와 걸이 턱을 덮는 쐐기. 아랫면 하나가 45° 로,
// 턱 경사면과 gv 만큼 떠서 나란하다가 바깥으로 그대로 이어져 위 벽 안쪽 면과 만난다.
// 코어 축을 도는 회전체라 턱 링과 둥근 면으로 맞닿고, 팔 원통 밖으로는 나가지 않는다.
// 출력할 때(코어 쪽 끝이 위) 아래를 향하는 면은 이 45° 면뿐이다.
module hook() {
    x0 = Rc + cl_out + gapc;
    xt = Rc + 1.2;                    // 갈고리 끝: 코어 벽에서 1.2 mm
    gv = 0.8;                         // 턱 경사면과의 위아래 틈
    k  = Rc + cl_out - cl_z;          // 턱 경사면: z = r − k
    al = asin((hook_w / 2) / x0);     // 갈고리가 코어를 감싸는 반각
    intersection() {
        arm_solid(R - 0.01);
        rotate(-al) rotate_extrude(angle = 2 * al)
            polygon([[xt, xt - k + gv], [R + 1 + k - gv, R + 1], [xt, R + 1]]);   // 45° 면은 벽에 닿을 때까지
    }
}

// 발꿈치: 팔 아래 벽 안쪽, 코어 쪽 끝에 붙는 덩어리. 코어 받침 링을 gapc 틈을 두고 마주 본다.
// 출력할 때(코어 쪽 끝이 위) 아래를 향하는 면은 45° 라 서포트가 없다.
module heel() {
    x0 = Rc + cl_out + gapc;
    zt = heel_z[1];
    d  = zt + R + 1;                  // 45° 면이 벽까지 내려가는 거리
    al = asin((hook_w / 2) / x0);
    intersection() {
        arm_solid(R - 0.01);
        rotate(-al) rotate_extrude(angle = 2 * al)
            polygon([[x0, -R - 1], [x0 + heel_l + d, -R - 1], [x0 + heel_l, zt], [x0, zt]]);
    }
}

// ---------- 코어 마디 (쓰는 좌표: 팔 축 z = 0. 가운데 층 마디는 z = −Hf/2 부터, 맨 아래 마디는 팔 아랫면 z = −R 부터) ----------
// 쌓기: 위 마디 바닥 속 모따기(45°)가 아래 마디 어깨(45°)에 면으로 앉아, 층 간격이 정확히 Hf 가 된다.
module core(z0 = -Hf / 2) {    // z0: 마디 바닥 높이. 다음 마디 바닥은 늘 Hf/2
    Rs = Rc - wc - clr;                  // 위 끝 꽂이 바깥 반지름
    zc = Hf / 2 - wc + ch - 0.1;         // 어깨(45°)가 시작하는 높이 (0.1 은 모델에서 두 면을 떼어 두는 몫)
    difference() {
        intersection() { union() {
            translate([0, 0, z0]) cylinder(h = zc - z0, r = Rc);
            // 위 끝 어깨와 꽂이: 45° 로 좁아져 spig 만큼 올라간다
            translate([0, 0, zc]) cylinder(h = Rc - Rs, r1 = Rc, r2 = Rs);
            translate([0, 0, zc]) cylinder(h = Rc - Rs + spig, r = Rs);
            // 걸이 턱 링: 단면이 위로 뾰족한 삼각형. 아래면 45°, 위 경사면은 코어 쪽으로 45° 내려간다
            rotate_extrude() polygon([
                [Rc - 0.01, cl_z - cl_out - 8], [Rc + cl_out, cl_z - 8 + 0.01 - 0.01],
                [Rc + cl_out, cl_z], [Rc + cl_out - 0.01, cl_z], [Rc + 0.6, cl_z - cl_out + 0.6],
                [Rc - 0.01, cl_z - cl_out + 0.6]]);
            // 받침 링: 발꿈치가 미는 곳. 아래면 45°, 바깥면은 세로
            rotate_extrude() polygon([
                [Rc - 0.01, heel_z[0] - cl_out], [Rc + cl_out, heel_z[0]],
                [Rc + cl_out, heel_z[1]], [Rc - 0.01, heel_z[1]]]);
        }
        translate([0, 0, z0]) cylinder(h = Hf + 2 * Rc, r = 2 * Rc); }   // 맨 아래 마디는 받침 링 아래를 자른다
        translate([0, 0, z0 - 1]) cylinder(h = zc - z0 + 1.01, r = Rc - wc);   // 속
        translate([0, 0, z0 - 0.01]) cylinder(h = ch + 0.01, r1 = Rc - wc + ch, r2 = Rc - wc);   // 바닥 속 모따기
        translate([0, 0, zc]) cylinder(h = Rc - Rs + 0.001, r1 = Rc - wc, r2 = Rs - wc);
        translate([0, 0, zc + (Rc - Rs)]) cylinder(h = spig + 1, r = Rs - wc);
    }
}

module floor_set(base = false) {
    core(base ? -R : -Hf / 2);
    for (a = [0, 90, 180, 270]) rotate(a) arm();
}

if (part == "floor") translate([0, 0, R]) floor_set(true);
else if (part == "floor_mid") floor_set();
else if (part == "tower") {      // 맨 아래 층(팔이 바닥에 놓임) + 둘째 층
    translate([0, 0, R]) { floor_set(true); translate([0, 0, Hf]) rotate(twist) floor_set(); }
}
else if (part == "arm")   translate([0, 0, reach]) rotate([0, 90, 0]) arm();     // 바깥 끝이 바닥, 코어 쪽이 위
else if (part == "core")  translate([0, 0, Hf / 2]) core();
else if (part == "core_base") translate([0, 0, R]) core(-R);
else if (part == "core_joint") {  // 쌓기 이음 시험: 코어 아래 끝 30 mm (받는 쪽) + 위 끝 어깨와 꽂이 (꽂는 쪽)
    zc = Hf / 2 - wc + ch - 0.1;
    translate([-Rc - 8, 0, 0]) intersection() { translate([0, 0, Hf / 2]) core(); cylinder(h = 30, r = 2 * Rc); }
    translate([Rc + 8, 0, 0]) intersection() { translate([0, 0, -(zc - 25)]) core(); cylinder(h = 100, r = 2 * Rc); }
}

echo(str("DIMS cross_span=", 2 * reach, " arm_D=", D, " core_D=", 2 * Rc, " floor_h=", Hf,
         " arm_print_h=", reach - (Rc + gapc)));
