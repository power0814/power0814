// 허브 화분 아파트 · 십자 층: 코어 기둥 + 원통 네 개 + 같이 쓰는 물길
//
// 쓰는 좌표: z 위, 코어 축 = z 축. 원통(팔) 넷이 코어에서 +x, +y, −x, −y 로 뻗는다.
// - 코어: 세로 원통 마디. 층마다 하나. 아래 끝 꽂이가 아래 마디 위 끝에 꽂힌다 (홈통처럼 위가 아래 속으로).
//   팔 위쪽 높이에 45° 걸이 턱(링), 아래쪽에 받침 링이 돈다.
// - 팔: 가로 원통. 바깥 끝은 막혔고, 코어 쪽 끝은 열려 있다 (위에 갈고리, 아래에 발꿈치, 옆은 이웃 팔과 45° 면).
//   갈고리가 걸이 턱에 걸리고 발꿈치가 받침 링을 밀어 짝힘으로 처짐을 받는다.
//   팔을 6 mm 들어 올려 바깥으로 빼고, 거꾸로 끼운다.
// - 물길: 맨 위 코어에 물을 부으면
//   1) 층마다 코어 속 받이 지붕(45° 원뿔)이 떨어지는 물을 다 받아 벽으로 보내고
//   2) 팔 쪽 구멍 넷과 홈통을 지나 팔 안 물받이로 떨어진다.
//   3) 물받이 가운데 물길을 따라 바깥 끝까지 갔다가 양쪽 칸을 거슬러 코어 쪽 넘침 둑을 넘고
//   4) 주둥이로 받침 링 위 홈통에 떨어져, 코어 벽 구멍으로 지붕 아래 코어 속에 들어가 아래층 지붕으로 떨어진다.
//   마개: 물받이 가운데 물길에 끼우면 그 팔은 윗물을 받지 않는다 (넘쳐 돌아가는 둑으로 바로 아래로).
//   맨 아래 층도 팔이 매달린 물길 층이다(필로티 없음). 그 코어가 팔 아래로 이어져 집수 바닥과 대각선 배수 밸브를 품고,
//   받침판 소켓에 꽂힌다. (처음에는 필로티였다: 바닥에 눕힌 팔이 코어 들림을 막지 못해 판으로 바꿨다)
//
// part = "floor"       받침판 + 맨 아래 층                         "floor_water"     그 물받이·마개·밸브
//        "floor_mid"   가운데 층 하나, 팔 축 z = 0                 "floor_mid_water" 그 물받이·마개
//        "tower"       받침판 + 맨 아래 층 + 둘째 층, 물 부품까지 (틈 검사용)
//        "arm" "core" "core_base" "plate" "core_joint" "tray" "gate" "basket" "tank" "valve_body" "valve_plug"   출력 방향
// openscad -o stl/cross_arm.stl -D 'part="arm"' cross_floor.scad

part = "floor";

// 축척: 1 이면 실물. 물 시험용 축소 모델(water_test.scad)은 k 만 바꿔 같은 파일을 쓴다.
// 위치와 크기는 k 배가 되지만, 틈·벽 두께·물길 최소 크기는 그대로 둔다.
// (틈을 줄이면 끼워지지 않고, 물길이 5 mm 아래로 작아지면 표면장력 때문에 물이 흐르지 않고 매달린다)
k      = 1;
// 크기
D      = 140 * k;    // 팔 원통 바깥 지름
w      = max(0.8, 1.6 * k);   // 팔 벽
reach  = 320 * k;    // 코어 축에서 팔 바깥 끝까지 (십자 폭 = 2 × reach)
cap    = max(1.2, 2.0 * k);   // 팔 바깥 끝 막음
mt     = max(0.8, 1.6 * k);   // 대각선 면 판 두께
Rc     = 45 * k;     // 코어 바깥 반지름
wc     = max(1.6, 2.5 * k);   // 코어 벽
Hf     = 270 * k;    // 층 간격 (팔 축에서 다음 층 팔 축까지). 7 층이면 맨 위 팔 윗면이 바닥에서 R + 6Hf + R = 1760
gapc   = 0.6;        // 팔과 코어 사이 틈
mgap   = 0.3;        // 이웃 팔과 대각선 면 사이 틈 (한쪽)
// 걸이 (프렌치 클리트)
cl_z   = 56 * k;     // 걸이 턱 꼭대기 높이 (팔 축 = 0 기준). 높을수록 발꿈치와의 팔길이가 길어진다
rim_t  = max(1.2, 1.5 * k);   // 받침 링 바깥 가장자리 턱 (물이 코어 밖으로 흘러내리지 않게)
cl_out = max(7 * k, 5 + rim_t);   // 턱이 코어 밖으로 나온 거리. 받침 링 홈통 너비(cl_out − rim_t)가 5 mm 아래로 줄지 않게
cl_h   = 8 * k;      // 걸이 턱 링의 세로 바깥면 높이
hook_w = 50 * k;     // 갈고리와 발꿈치 너비 (코어 쪽 끝에서 잰 현)
// 받침 (발꿈치)
heel_z = [-68, -54] * k;  // 받침 링과 발꿈치가 맞닿는 높이 범위 (낮을수록 좋다. 팔 아래 벽 안쪽이 −68.4)
heel_l = 8 * k;      // 발꿈치가 팔 끝에서 바깥으로 차지하는 길이
// 심는 창 (팔 위쪽)
win    = [140, 290] * k;  // 창이 놓이는 x 범위 (코어 축 기준)
win_w  = 64 * k;
// 쌓기
twist  = 0;          // 층마다 돌리는 각도. 0 이면 팔이 위아래로 한 줄로 선다 (45 면 엇갈림)
spig   = 40 * k;    // 꽂이 길이. 지름의 약 절반: 한쪽 무게를 받아도 위 마디가 테두리를 축으로 들리지 않게 (18 → 40)
clr    = 0.15;      // 꽂이 틈 (한쪽). 0.25 는 반 크기 출력에서 헐렁했다
ch     = 1.5 * k;    // 코어 위 끝 속 모따기. 위 마디 어깨(45°)가 이 면에 앉는다. 남는 이음 줄눈 = wc − ch
// 물길
out_w  = max(8, 13 * k);     // 팔로 나가는 구멍과 홈통 물길 너비
out_h  = max(6, 8 * k);
roof_z = min(30 * k, cl_z - cl_out - cl_h - out_h - 1.3);   // 받이 지붕이 코어 벽 안쪽과 만나는 높이 = 구멍 바닥. 구멍이 걸이 턱 링 아래에 오게
roof_t = max(1.2, 2.0 * k);
gut_a  = 20;         // 받침 링 홈통 구멍: 팔 축에서 ± 이 각도
gut_w  = max(6, 12 * k);
gut_h  = max(4, 5 * k);
rim_h  = max(1, 2 * k);
// 물받이 (팔 안에 넣는 별도 부품)
tw     = max(1.2, 1.6 * k);
tr_b   = 20 * k;     // 몸통 바닥 반너비 (바깥 면). 옆벽은 45° 로 벌어진다
tr_zb  = -round(10 * sqrt(pow(D / 2 - w - 0.3, 2) - pow(tr_b, 2))) / 10;   // 몸통 바닥 (바깥 면): 바닥 모서리가 팔 안쪽 면에서 0.3 안쪽
tr_zh  = -50 * k;    // 머리 바닥 (바깥 면). 발꿈치 위
lv_main = -32 * k;   // 물높이 = 넘침 둑 꼭대기 (창에서 물까지 약 10 cm, 깊이 약 3 cm)
lv_by  = lv_main + max(2, 3 * k);    // 마개를 닫았을 때 넘쳐 돌아가는 둑 (머리의 칸막이)
lv_div = lv_by + max(1.5, 2 * k);    // 옆 물길과 뿌리 칸 사이 칸막이 꼭대기
tr_rim = lv_div + max(1, 2 * k);     // 물받이 테두리
tr_hw  = 48 * k;     // 물받이 위쪽 반너비 (세로벽). 팔 코어 쪽 열린 끝(반너비 약 50)을 지나가야 한다
ch_hw  = max(4, 8 * k);      // 머리: 들어오는 물 칸(−y ~ +ch_hw)과 골(+y) 사이 칸막이 자리
ch_f   = max(5, 8 * k);      // 옆 물길 바닥 너비
tr_x0  = max(56 * k, Rc + cl_out + gapc + 2);   // 물받이 코어 쪽 끝 (팔 끝보다 바깥)
tr_head = ceil(max(tr_x0 + 10, Rc + cl_out + gapc + heel_l + (heel_z[1] - tr_zb) + 2));   // 머리 끝 = 넘침 둑. 몸통 바닥이 발꿈치를 비켜 가는 곳
tr_x   = [tr_x0, 316 * k];
chute_x = round(tr_x0 + 0.55 * (tr_head - tr_x0));   // 홈통 끝 (코어 축에서). 물이 여기서 물받이 머리의 가운데 물길로 떨어진다
div_end = 286 * k;   // 칸막이 끝. 이 너머 바깥 끝에서 옆 물길이 뿌리 칸으로 열린다
gate_x = 246 * k;    // 마개 자리 (창 아래, 손이 닿는다)
sp_y   = [max(ch_hw + tw + 0.5, 10.5 * k), max(ch_hw + tw + 8, 30 * k)];   // 넘친 물 주둥이 (+y 쪽 하나)
ch_y   = -(tr_b + tw - tw * sqrt(2));   // 옆 물길 바깥 끝 (물받이 안 바닥의 −y 모서리)
dv_y   = ch_y + ch_f;    // 옆 물길과 뿌리 칸 사이 칸막이의 물길 쪽 면
// 심는 바구니 (창으로 넣어 물까지 내린다)
bk_x   = [178, 236] * k;
bk_y   = [max(-8 * k, dv_y + tw + 1.5), min(28 * k, 32 * k - 2)];
bk_w   = max(1.2, 1.6 * k);
sp_r   = Rc + 1.5;   // 주둥이 끝 (코어 축에서). 받침 링 홈통 위
sp_h   = max(5, 8 * k);      // 주둥이 옆벽 높이 (바닥 위)
// 맨 아래 층과 받침판
// 맨 아래 층도 팔이 매달린 물길 층이다 (필로티 없음). 그 코어는 팔 아래로 짧은 기둥이 이어져
// 집수 바닥과 배수 밸브를 품고, 받침판의 소켓에 깊이 꽂힌다. 탑이 넘어지려면 판 전체가 들려야 한다.
sump_z = -D / 2 - 25;    // 집수 바닥(원뿔)이 코어 벽 안쪽과 만나는 높이 = 배수 관 바닥. 밸브 손잡이 윗면(+22)이 팔 아랫면 3 mm 아래
sock_h = max(20, 50 * k);   // 받침판 소켓 깊이 (코어 지름의 약 절반)
pl_w   = 480 * k;    // 받침판 한 변
pl_t   = max(6, 10 * k);    // 받침판 두께
sl_w   = max(2, 3 * k);     // 소켓 벽
dk_i   = 4;          // 배수 관 물길 반너비
dk_w   = 1.8;        // 배수 관 벽
vx     = max(84 * k, Rc + 23);   // 밸브 마개 자리 (코어 축에서, 대각선)
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
    translate([0, 0, R / 4]) linear_extrude(height = R)   // 위쪽 벽을 세로로 뚫는다 (둥근 벽이라 얇게 자르면 창이 좁아진다)
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

// ---------- 코어 마디 (쓰는 좌표: 팔 축 z = 0. 가운데 층 마디 몸통은 z ≈ −Hf/2 부터, 맨 아래 마디는 팔 아랫면 z = −R 부터) ----------
// 쌓기: 위 마디 아래 끝의 어깨(45°)가 아래 마디 위 끝 속 모따기에 면으로 앉아, 층 간격이 정확히 Hf 가 된다.
// 위 마디 꽂이가 아래 마디 속으로 들어가므로, 코어 속을 타고 내려온 물은 이음 틈으로 새지 않고 아래로 떨어진다.
function core_low() = -Hf / 2 + (wc - ch + 0.1) - (wc + clr) - spig;   // 가운데 마디 아래 꽂이 끝 높이
function chute_f(x) = roof_z - (x - (Rc - wc)) * tan(7);   // 홈통 물길 바닥: 바깥으로 7° 내려간다
module roof_cone(zr) {          // 받이 지붕 / 집수 바닥: 가운데가 높은 45° 원뿔, 벽 안쪽에서 높이 zr
    Ri = Rc - wc;
    tv = roof_t * sqrt(2);
    rotate_extrude() polygon([[0, zr + Ri], [Ri + 0.4, zr - 0.4], [Ri + 0.4, zr - 0.4 - tv], [0, zr + Ri - tv]]);
}
module chute() {                // 팔로 나가는 홈통 (+x 팔). 아랫면 45° 라 코어를 세워 뽑을 때 서포트가 없다
    x0 = Rc - wc - 0.3;
    zt = chute_f(chute_x) - 2;
    hw = out_w / 2 + 1.6;
    translate([0, hw, 0]) rotate([90, 0, 0]) linear_extrude(2 * hw)
        polygon([[x0, zt - (chute_x - x0)], [chute_x, zt], [chute_x, chute_f(chute_x) + 6], [x0, roof_z + 6]]);
}
module chute_drip() {           // 홈통 끝 아랫면의 물끊기 홈: 적게 흐를 때 물이 아랫면을 타고 코어 쪽으로 되돌아가지 않게
    zt = chute_f(chute_x) - 2;
    xg = chute_x - 2.2;
    zu = zt - (chute_x - xg);
    n = [-1, 1] / sqrt(2);
    hw = out_w / 2 + 2.6;
    translate([0, hw, 0]) rotate([90, 0, 0]) linear_extrude(2 * hw)
        polygon([[xg - 0.7, zu - 0.7] - 0.4 * n, [xg + 0.7, zu + 0.7] - 0.4 * n, [xg, zu] + 1.0 * n]);
}
module chute_channel() {
    x0 = Rc - wc - 1;
    translate([0, out_w / 2, 0]) rotate([90, 0, 0]) linear_extrude(out_w)
        polygon([[x0, chute_f(x0)], [chute_x + 1, chute_f(chute_x + 1)], [chute_x + 1, roof_z + out_h],
                 [x0, roof_z + out_h]]);
}
module duct2d(d = 0) {          // 배수 관 물길 단면: 바닥 평평, 지붕 45° (눕혀 뽑아도 세워 뽑아도 서포트가 없다)
    offset(delta = d) polygon([[-dk_i, 0], [dk_i, 0], [dk_i, 3], [0, 3 + dk_i], [-dk_i, 3]]);
}
module duct_prism(d, x0, x1) {  // x 방향으로 뻗은 배수 관 단면
    translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) duct2d(d);
}
function core_bot() = sump_z - 11.5 - 3 - sock_h;   // 맨 아래 코어 바닥 = 받침판 윗면 (밸브 자리 아랫면과 소켓 윗끝 사이 3 mm)
module core(z0 = -Hf / 2, base = false) {
    // base = true: 맨 아래 코어. 가운데 마디와 같은 물길 층(턱, 홈통, 받이 지붕, 홈통 구멍)에
    // 꽂이 대신 아래로 기둥이 이어져 집수 바닥과 배수 관 자리를 품고, 바닥(z0)은 받침판 소켓에 앉는다.
    Ri = Rc - wc;
    Rs = Ri - clr;                       // 아래 끝 꽂이 바깥 반지름
    zb = -Hf / 2 + (wc - ch + 0.1);      // 가운데 마디 몸통 아래 끝. 그 아래로 어깨(45°)와 꽂이 (0.1 은 모델에서 두 면을 떼어 두는 몫)
    bot = base ? z0 : zb;
    difference() {
        intersection() {
            union() {
                translate([0, 0, bot]) cylinder(h = Hf / 2 - bot, r = Rc);
                if (!base) {
                    translate([0, 0, zb - (Rc - Rs)]) cylinder(h = Rc - Rs + 0.001, r1 = Rs, r2 = Rc);
                    translate([0, 0, zb - (Rc - Rs) - spig]) cylinder(h = spig + 0.001, r = Rs);
                }
                // 걸이 턱 링: 단면이 위로 뾰족한 삼각형. 아래면 45°, 위 경사면은 코어 쪽으로 45° 내려간다
                rotate_extrude() polygon([
                    [Rc - 0.01, cl_z - cl_out - cl_h], [Rc + cl_out, cl_z - cl_h],
                    [Rc + cl_out, cl_z], [Rc + cl_out - 0.01, cl_z], [Rc + 0.6, cl_z - cl_out + 0.6],
                    [Rc - 0.01, cl_z - cl_out + 0.6]]);
                // 받침 링: 발꿈치가 미는 곳. 아래면 45°, 바깥면은 세로. 윗면은 홈통 (바깥 가장자리 턱)
                rotate_extrude() polygon([
                    [Rc - 0.01, heel_z[0] - cl_out], [Rc + cl_out, heel_z[0]],
                    [Rc + cl_out, heel_z[1] + rim_h], [Rc + cl_out - rim_t, heel_z[1] + rim_h],
                    [Rc + cl_out - rim_t, heel_z[1]], [Rc - 0.01, heel_z[1]]]);
                for (a = [0, 90, 180, 270]) rotate(a) chute();
                if (base) rotate(45) translate([0, 0, sump_z]) hull() {   // 배수 관 꽂는 자리 (아랫면 45°). 팔 아래, 대각선
                    duct_prism(dk_w + 0.2 + 2.5, Rc - 1, Rc + 6);
                    translate([0, 0, -7]) duct_prism(dk_w + 0.2 + 2.5, Rc - 1, Rc - 0.5);
                }
            }
            translate([0, 0, base ? z0 : -Hf]) cylinder(h = 2 * Hf, r = 3 * Rc);   // 맨 아래 마디는 바닥 아래를 자른다
        }
        translate([0, 0, bot - (base ? 1 : 0.01)]) cylinder(h = Hf / 2 - bot + 2, r = Ri);   // 속
        translate([0, 0, Hf / 2 - ch]) cylinder(h = ch + 0.01, r1 = Ri, r2 = Ri + ch);       // 위 끝 속 모따기
        if (!base) {
            translate([0, 0, zb - (Rc - Rs) - 0.001]) cylinder(h = Rc - Rs + 0.002, r1 = Rs - wc, r2 = Ri);
            translate([0, 0, zb - (Rc - Rs) - spig - 1]) cylinder(h = spig + 1.001, r = Rs - wc);
        }
        for (a = [0, 90, 180, 270]) rotate(a) {
            chute_channel();                                       // 팔로 나가는 구멍과 홈통 물길
            chute_drip();
            for (sg = [-1, 1]) rotate(sg * gut_a)                   // 받침 링 홈통에서 코어 속으로 돌아가는 구멍 (위는 45° 뾰족)
                translate([Ri - 1, 0, heel_z[1]]) rotate([90, 0, 90]) linear_extrude(wc + 2)
                    polygon([[-gut_w / 2, 0], [gut_w / 2, 0], [gut_w / 2, gut_h], [0, gut_h + gut_w / 2], [-gut_w / 2, gut_h]]);
        }
        if (base) rotate(45) translate([0, 0, sump_z]) duct_prism(dk_w + 0.2, Ri - 1, Rc + 7);   // 배수 관 구멍
    }
    roof_cone(roof_z);                    // 받이 지붕
    if (base) difference() {              // 집수 바닥 (맨 아래 코어, 팔 아래)
        roof_cone(sump_z);
        // 집수 바닥은 관 물길(바닥 = sump_z)만큼만 판다. 밸브 관이 끼는 넓은 구멍(바닥 sump_z − 2)은
        // 코어 벽 안쪽(Ri 바깥)에서만 판다: 벽 안쪽 공간에서 넓게 파면 원뿔을 뚫어 물이 코어 아래로 샌다
        rotate(45) translate([0, 0, sump_z]) {
            duct_prism(0, Rc - wc - 1, Rc + 7);
            duct_prism(dk_w + 0.2, Rc - wc, Rc + 7);
        }
    }
}

// ---------- 받침판 ----------
// 맨 아래 코어가 소켓(틈 clr, 깊이 sock_h)에 꽂힌다. 판 윗면 = 코어 바닥 = core_bot().
// 아랫면 네 모서리에 TPU 패드 홈 (지름 20.4, 깊이 1.5: bookshelf/pad.scad 의 패드).
// 출력: 아랫면을 판에 대고 그대로 (소켓 벽은 세로, 밑동은 45°).
module plate() {
    zt = core_bot();
    ri = Rc + clr;
    ro = ri + sl_w;
    c = pl_t / 2;                         // 윗 모서리 모따기
    difference() {
        union() {
            translate([0, 0, zt - pl_t]) hull() {
                translate([-pl_w / 2, -pl_w / 2, 0]) cube([pl_w, pl_w, pl_t - c]);
                translate([-pl_w / 2 + c, -pl_w / 2 + c, 0]) cube([pl_w - 2 * c, pl_w - 2 * c, pl_t]);
            }
            translate([0, 0, zt - 0.01]) cylinder(h = sock_h + 0.01, r = ro);
            translate([0, 0, zt - 0.01]) cylinder(h = 2 * sl_w + 0.01, r1 = ro + 2 * sl_w, r2 = ro);   // 소켓 밑동 (45°)
        }
        translate([0, 0, zt - 0.2]) cylinder(h = sock_h + 1, r = ri);              // 소켓 (바닥에 0.2 홈: 코어 바닥 모서리가 뜨지 않게)
        translate([0, 0, zt + sock_h - 0.8]) cylinder(h = 0.81, r1 = ri, r2 = ri + 0.8);   // 소켓 입구 모따기
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * (pl_w / 2 - 25), sy * (pl_w / 2 - 25), zt - pl_t - 1])
            cylinder(h = 1.5 + 1, d = 20.4);
    }
}

// ---------- 물받이 (쓰는 좌표 = 팔 좌표, +x 팔 안) ----------
// 단면: 바닥 반너비 tr_b 에서 45° 로 벌어지다가 반너비 tr_hw 부터 세로벽. 머리(코어 쪽)는 발꿈치 위로 바닥이 얕다.
// 칸: −y 벽을 따라 옆 물길, 나머지는 창 아래 넓은 뿌리 칸 하나.
//   홈통 물이 머리 가운데(들어오는 칸)로 떨어져 옆 물길로 바깥 끝까지 가고, 뿌리 칸을 거슬러 와
//   머리 앞 넘침 둑(lv_main)을 넘어 +y 쪽 골로, 다시 주둥이로 나간다.
// 마개(gate)를 옆 물길에 끼우면 들어오는 칸이 머리 칸막이(lv_by)를 넘쳐 바로 골로 가므로, 이 팔은 윗물을 받지 않는다.
// 출력: −y 아래 45° 벽을 판에 대고 눕힌다 (part = "tray"). 모든 면이 45° 안쪽이라 서포트가 없다.
function prof(zb, top = tr_rim + 10) =
    let(zv = tr_zb + (tr_hw - tr_b), hb = tr_b + (zb - tr_zb))
    zb >= zv ? [[-tr_hw, zb], [tr_hw, zb], [tr_hw, top], [-tr_hw, top]]
             : [[-hb, zb], [hb, zb], [tr_hw, zv], [tr_hw, top], [-tr_hw, top], [-tr_hw, zv]];
module xprism(poly, x0, x1) { translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) polygon(poly); }
module xprism_off(poly, d, x0, x1) { translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) offset(delta = d) polygon(poly); }
module xbox(x, y, z) { translate([x[0], y[0], z[0]]) cube([x[1] - x[0], y[1] - y[0], z[1] - z[0]]); }
module tray() {
    fl_h = tr_zh + tw;                   // 머리 안 바닥
    yo = tr_hw + 2;
    intersection() {
        union() {
            difference() {
                union() {
                    xprism(prof(tr_zh), tr_x[0], tr_head + 0.01);
                    xprism(prof(tr_zb), tr_head, tr_x[1]);
                }
                xprism_off(prof(tr_zh), -tw, tr_x[0] + tw, tr_head + tw + 0.01);   // 속: 머리, 몸통 (벽 tw)
                xprism_off(prof(tr_zb), -tw, tr_head + tw, tr_x[1] - tw);
            }
            // 머리: 들어오는 칸(y < ch_hw)과 골 사이 칸막이 = 우회 둑
            xbox([tr_x[0], tr_head + tw], [ch_hw, ch_hw + tw], [tr_zb, lv_by]);
            // 몸통: 옆 물길과 뿌리 칸 사이 칸막이
            xbox([tr_head, div_end], [dv_y, dv_y + tw], [tr_zb, lv_div]);
            // 머리와 몸통 경계: 골 앞은 넘침 둑(lv_main), 들어오는 칸 앞(뿌리 칸 쪽)은 칸막이 높이
            xbox([tr_head, tr_head + tw], [ch_hw, yo], [tr_zb, lv_main]);
            xbox([tr_head, tr_head + tw], [dv_y, ch_hw + tw], [tr_zb, lv_div]);
            // 마개 기둥: 마개 자리에서 옆 물길을 네모나게 (칸막이 쪽, 바깥 벽 쪽)
            xbox([gate_x - 4, gate_x + 4], [dv_y, dv_y + 4], [tr_zb, lv_div]);
            xbox([gate_x - 4, gate_x + 4], [-yo, ch_y], [tr_zb, lv_div]);
        }
        union() {                         // 바깥 모양 안으로 자르고, 위는 테두리까지
            xprism(prof(tr_zh, tr_rim), tr_x[0], tr_head + 0.01);
            xprism(prof(tr_zb, tr_rim), tr_head, tr_x[1]);
        }
    }
    // 주둥이 (+y 쪽, 머리 코어 쪽 벽을 뚫고 받침 링 홈통 위로)
    intersection() {
        xbox([0, tr_x[0] + tw], [sp_y[0] - tw, sp_y[1] + tw], [tr_zh, fl_h + sp_h]);
        difference() { cylinder(h = 400, r = 400, center = true); cylinder(h = 400, r = sp_r, center = true); }
    }
}
module tray_cut() {             // 주둥이 물길 + 주둥이 아래 물끊기 홈 + 마개 홈
    intersection() {
        difference() { cylinder(h = 400, r = sp_r + 2.2, center = true); cylinder(h = 400, r = sp_r + 1.2, center = true); }
        xbox([0, tr_x[0]], [sp_y[0] - tw - 1, sp_y[1] + tw + 1], [tr_zh - 0.5, tr_zh + 0.6]);
    }
    xbox([0, tr_x[0] + tw + 0.5], [sp_y[0], sp_y[1]], [tr_zh + tw, tr_zh + tw + sp_h + 1]);
    xbox([gate_x - 1.2, gate_x + 1.2], [ch_y - 2, ch_y + 0.01], [tr_zb + tw - 0.01, lv_div + 1]);
    xbox([gate_x - 1.2, gate_x + 1.2], [dv_y - 0.01, dv_y + 2], [tr_zb + tw - 0.01, lv_div + 1]);
}
module tray_full() { difference() { tray(); tray_cut(); } }

// 마개: 옆 물길을 막는 판 + 창 쪽으로 올라오는 손잡이. 판에 눕혀 뽑는다
module gate() {
    t = 2.0; c = 0.3;
    yc = (ch_y + dv_y) / 2;
    hy = (dv_y - ch_y) / 2 + 2 - c;
    z0 = tr_zb + tw + c;
    translate([gate_x - t / 2, yc, 0]) rotate([90, 0, 90]) linear_extrude(t) difference() {
        union() {
            translate([-hy, z0]) square([2 * hy, lv_div - z0]);
            translate([-max(2, 3 * k), z0]) square([2 * max(2, 3 * k), 40 * k - z0]);
            translate([-8 * k, 28 * k]) square([16 * k, 14 * k]);
        }
        translate([0, 35 * k]) circle(r = 4 * k, $fn = 32);
    }
}

// 심는 바구니: 창 긴 변 두 곳에 걸치는 걸쇠 + 뿌리 칸 물속까지 내려가는 몸통.
// 배지(하이드로볼 등)를 채운다. 아래쪽 벽의 틈으로 물과 뿌리가 드나든다. 뒤집어 뽑는다 (걸쇠가 판에).
module basket() {
    ze = sqrt(R * R - pow(win_w / 2, 2));     // 창 긴 변에서 팔 바깥면 높이
    zt = ze + max(2, 3 * k);                  // 걸쇠 윗면
    zb = lv_main - max(4, 6 * k);             // 바닥 꼭짓점: 물속
    hy = (bk_y[1] - bk_y[0]) / 2;
    yc = (bk_y[0] + bk_y[1]) / 2;
    lug = max(4, 6 * k);
    sl = max(1.6, 2 * k);                     // 틈 너비
    difference() {
        union() {
            // 몸통: 바닥은 45° V (뒤집어 뽑을 때 지붕이 된다)
            hull() {
                xbox(bk_x, bk_y, [zb + hy, zt]);
                xbox(bk_x, [yc - 0.5, yc + 0.5], [zb, zb + 1]);
            }
            for (x = [bk_x[0], bk_x[1] - lug]) xbox([x, x + lug], [-win_w / 2 - 5 * k - 1, win_w / 2 + 5 * k + 1], [ze, zt]);
        }
        hull() {                              // 속
            xbox([bk_x[0] + bk_w, bk_x[1] - bk_w], [bk_y[0] + bk_w, bk_y[1] - bk_w], [zb + hy, zt + 1]);
            xbox([bk_x[0] + bk_w, bk_x[1] - bk_w], [yc - 0.1, yc + 0.1], [zb + bk_w * sqrt(2), zb + bk_w * sqrt(2) + 0.2]);
        }
        for (x = [bk_x[0] + 5 * k + sl : 4 * sl : bk_x[1] - 5 * k - sl])   // 물·뿌리 틈: V 바닥을 가로질러 물높이 위까지
            xbox([x - sl / 2, x + sl / 2], [bk_y[0] - 1, bk_y[1] + 1], [zb - 1, lv_main + 0.3 * (ze - lv_main)]);
    }
}

// ---------- 물 추 통 (구조 시험용) ----------
// 물받이 자리에 넣는 막힌 통. 물이 흐르지 않고 담긴 채로 팔에 무게를 준다 (붓는 mL = 무게 g).
// 바닥은 물받이와 같아(바닥 모서리가 팔 안쪽 면에 얹힌다) 무게가 같은 자리에 실린다. 칸막이·둑·주둥이가 없다.
// 폭은 팔의 코어 쪽 입구(대각선 판 사이)보다 좁게, 높이는 갈고리 아래로 잡아 그대로 밀어 넣는다:
//   팔을 걸기 전에 통을 tk_lift 만큼 띄워(발꿈치를 넘게) 코어 쪽 열린 끝으로 밀어 넣고 내려놓는다.
// 채우기·빼기: 심는 창으로 계량컵이나 주사기. 양 끝 안쪽 벽에 25 mL 마다 눈금 턱 (50 mL 마다 길게).
// 출력: 바닥이 판, 위가 열린 채로 세운다 (45° 와 세로벽뿐이라 서포트가 없다).
tk_w   = max(1.6, tw);           // 통 벽 (물이 새지 않게 물받이보다 두껍게)
tk_c   = (mgap + mt) * sqrt(2);  // 대각선 판 안쪽 면: |y| = x − tk_c
tk_rc  = Rc + cl_out + gapc;     // 팔 끝을 자른 원 (코어 둘레)
tk_hw  = min(tr_hw, (tk_c + sqrt(2 * tk_rc * tk_rc - tk_c * tk_c)) / 2 - tk_c - 0.4);   // 통 반너비: 입구에서 0.4 남게
tk_lift = heel_z[1] - tr_zb + 0.6;                    // 넣을 때 띄우는 높이 (발꿈치 위)
tk_top = cl_z - cl_out + 2.0 - tk_lift - 0.5;         // 통 위 끝: 띄워도 갈고리 아랫면(cl_z − cl_out + 2)에 안 닿게
tk_x   = [tr_head, tr_x[1]];     // 몸통만 (머리 자리는 발꿈치 위라 뺀다)
tk_L   = tk_x[1] - tk_x[0] - 2 * tk_w;          // 속 길이
tk_z0  = tr_zb + tk_w;                           // 속 바닥
tk_hb  = tr_b + tk_w - tk_w * sqrt(2);           // 속 바닥 반너비
tk_zv  = tr_zb + (tk_hw - tr_b) - tk_w + tk_w * sqrt(2);   // 45° 벽이 세로벽으로 바뀌는 높이
function tk_prof(top) = let(zv = tr_zb + (tk_hw - tr_b))
    [[-tr_b, tr_zb], [tr_b, tr_zb], [tk_hw, zv], [tk_hw, top], [-tk_hw, top], [-tk_hw, zv]];
function tk_av() = (2 * tk_hb + (tk_zv - tk_z0)) * (tk_zv - tk_z0);
function tk_vol(z) = tk_L * (z <= tk_zv ? (2 * tk_hb + (z - tk_z0)) * (z - tk_z0)
                                         : tk_av() + 2 * (tk_hw - tk_w) * (z - tk_zv));   // mm³
function tk_z(ml) = let(a = ml * 1000 / tk_L)
    a <= tk_av() ? tk_z0 - tk_hb + sqrt(tk_hb * tk_hb + a) : tk_zv + (a - tk_av()) / (2 * (tk_hw - tk_w));
module tank() {
    difference() {
        translate([tk_x[0], 0, 0]) rotate([90, 0, 90]) linear_extrude(tk_x[1] - tk_x[0]) polygon(tk_prof(tk_top));
        translate([tk_x[0] + tk_w, 0, 0]) rotate([90, 0, 90]) linear_extrude(tk_L)
            offset(delta = -tk_w) polygon(tk_prof(tk_top + 5));
    }
    // 눈금 턱: 윗면이 눈금, 아랫면 45°
    for (ml = [25 : 25 : floor(tk_vol(tk_top - 1.5) / 25000) * 25], e = [0, 1]) {
        xw = e == 0 ? tk_x[0] + tk_w : tk_x[1] - tk_w;
        s = e == 0 ? 1 : -1;
        hl = ml % 50 == 0 ? 6 : 3;
        z = tk_z(ml);
        translate([0, hl, 0]) rotate([90, 0, 0]) linear_extrude(2 * hl)
            polygon([[xw - s * 0.01, z - 0.8], [xw - s * 0.01, z], [xw + s * 0.8, z]]);
    }
}
echo(str("TANK k=", k, " hw=", tk_hw, " top=", tk_top, " lift=", tk_lift, " cap_mL=", round(tk_vol(tk_top - 1.5) / 1000), " L=", tk_L));

// ---------- 배수 밸브 (맨 아래 마디, 대각선) ----------
// 몸통: 코어 구멍에 꽂히는 배수 관 + 마개 통 + 호스 꼭지. 바닥이 평평해 그대로 눕혀 뽑는다.
// 마개(plug): 테이퍼 축에 물길 구멍. 손잡이가 관과 나란하면 열림, 직각이면 닫힘.
// 쓰는 좌표: x = 대각선 따라 코어 축에서, z = 0 이 배수 관 물길 바닥 (= sump_z)
module valve_body() {
    xs = Rc - wc + 0.1;
    hz = 16;                              // 마개 통 높이 (관 물길 바닥 위)
    bz = -dk_w + 4.5;                     // 호스 꼭지 축 높이
    intersection() {
        difference() {
            union() {
                duct_prism(dk_w, xs, vx);
                difference() {               // 멈춤 턱 (아래는 비워 둔다: 바닥이 평평해야 한다)
                    duct_prism(dk_w + 1.5, Rc + 6.5, Rc + 8.5);
                    translate([Rc, -20, -dk_w - 5]) cube([20, 40, 5]);
                }
                translate([vx, 0, -dk_w]) cylinder(h = hz + dk_w, r = 11);
                translate([vx, 0, bz]) rotate([0, 90, 0]) cylinder(h = 32, r = 4.5);
                for (k = [14, 22]) translate([vx + k, 0, bz]) rotate([0, 90, 0]) cylinder(h = 5, r1 = 5.3, r2 = 4.5);
            }
            duct_prism(0, xs - 1, vx);
            translate([vx, 0, -dk_w - 0.01]) cylinder(h = hz + dk_w + 0.02, r1 = 5.6, r2 = 6.2);
            translate([vx, 0, bz]) rotate([0, 90, 0]) rotate(45) cylinder(h = 33, r = 2.5, $fn = 4);   // 꼭지 속 (마름모: 눕혀 뽑아도 된다)
        }
        translate([0, -50, -dk_w]) cube([200, 100, 60]);
    }
}
module valve_plug() {
    hz = 16;
    difference() {
        union() {
            translate([0, 0, -dk_w]) cylinder(h = hz + dk_w, r1 = 5.45, r2 = 6.05);
            translate([-17, -3.5, hz]) cube([34, 7, 6]);
            translate([0, 0, hz]) cylinder(h = 6, r = 7.5);          // 손잡이 가운데 원판 (뒤집어 뽑을 때 축을 받친다)
        }
        duct_prism(0, -8, 8);
    }
}

module floor_set(base = false) {
    if (base) { core(core_bot(), true); plate(); }
    else core();
    for (a = [0, 90, 180, 270]) rotate(a) arm();
}
module water_set(base = false) {
    for (a = [0, 90, 180, 270]) rotate(a) { tray_full(); basket(); gate(); }
    if (base) rotate(45) translate([0, 0, sump_z]) { valve_body(); translate([vx, 0, 0]) valve_plug(); }
}
function base_lift() = pl_t - core_bot();   // 맨 아래 층 팔 축 높이 (탁자에서)

if (part == "floor") translate([0, 0, base_lift()]) floor_set(true);
else if (part == "floor_water") translate([0, 0, base_lift()]) water_set(true);
else if (part == "floor_mid") floor_set();
else if (part == "floor_mid_water") water_set();
else if (part == "tower") {      // 받침판 + 맨 아래 층 + 둘째 층, 물 부품까지
    translate([0, 0, base_lift()]) {
        floor_set(true); water_set(true);
        translate([0, 0, Hf]) rotate(twist) { floor_set(); water_set(); }
    }
}
else if (part == "arm")   translate([0, 0, reach]) rotate([0, 90, 0]) arm();     // 바깥 끝이 바닥, 코어 쪽이 위
else if (part == "core")  translate([0, 0, -core_low()]) core();      // 아래 꽂이 끝이 바닥
else if (part == "core_base") translate([0, 0, -core_bot()]) core(core_bot(), true);
else if (part == "plate") translate([0, 0, pl_t - core_bot()]) plate();
else if (part == "core_joint") {  // 쌓기 이음 시험: 코어 아래 끝 어깨·꽂이 (꽂는 쪽) + 위 끝 30 mm (받는 쪽)
    zb = -Hf / 2 + (wc - ch + 0.1);
    translate([-Rc - 8, 0, 0]) intersection() { translate([0, 0, -core_low()]) core(); cylinder(h = zb + 25 - core_low(), r = 2 * Rc); }
    translate([Rc + 8, 0, 0]) intersection() { translate([0, 0, -(Hf / 2 - 30)]) core(); cylinder(h = 31, r = 2 * Rc); }
}
else if (part == "tray") translate([0, 0, (tr_b - tr_zb) / sqrt(2)]) rotate([45, 0, 0]) tray_full();
else if (part == "gate") translate([0, 0, 1]) rotate([0, -90, 0]) translate([-gate_x, 0, 0]) gate();
else if (part == "tank") translate([-tk_x[0], 0, -tr_zb]) tank();
else if (part == "basket") translate([-bk_x[0], 0, sqrt(R * R - pow(win_w / 2, 2)) + max(2, 3 * k)]) rotate([180, 0, 0]) basket();
else if (part == "valve_body") translate([0, 0, dk_w]) valve_body();
else if (part == "valve_plug") translate([0, 0, 16 + 6]) rotate([180, 0, 0]) valve_plug();

echo(str("DIMS cross_span=", 2 * reach, " arm_D=", D, " core_D=", 2 * Rc, " floor_h=", Hf,
         " arm_print_h=", reach - (Rc + gapc), " base_core_h=", Hf / 2 - core_bot(), " base_axis_from_table=", base_lift(),
         " plate=", pl_w, " plate_fits_bed=", pl_w <= 320));
