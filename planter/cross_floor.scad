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
//   맨 아래 층은 필로티: 팔이 바닥에 놓이고 물길에서 빠진다. 그 코어 위쪽이 집수조이고 대각선에 배수 밸브가 있다.
//
// part = "floor"       맨 아래 층 (팔이 바닥에 놓임)              "floor_water"     그 물받이·밸브
//        "floor_mid"   가운데 층 하나, 팔 축 z = 0                 "floor_mid_water" 그 물받이·마개
//        "tower"       맨 아래 층 + 둘째 층, 물 부품까지 (틈 검사용)
//        "arm" "core" "core_base" "core_joint" "tray" "gate" "valve_body" "valve_plug"   출력 방향
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
spig   = 18 * k;
clr    = 0.25;
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
tr_rim = -36 * k;
lv_main = -44 * k;   // 물높이 = 넘침 둑 꼭대기
lv_by  = -40 * k;    // 마개를 닫았을 때 넘쳐 돌아가는 둑 (머리의 칸막이)
lv_div = -37 * k;    // 몸통의 가운데 물길 칸막이 꼭대기
ch_hw  = max(4, 8 * k);      // 가운데 물길 안 반너비
tr_x0  = max(56 * k, Rc + cl_out + gapc + 2);   // 물받이 코어 쪽 끝 (팔 끝보다 바깥)
tr_head = ceil(max(tr_x0 + 10, Rc + cl_out + gapc + heel_l + (heel_z[1] - tr_zb) + 2));   // 머리 끝 = 넘침 둑. 몸통 바닥이 발꿈치를 비켜 가는 곳
tr_x   = [tr_x0, 316 * k];
chute_x = round(tr_x0 + 0.55 * (tr_head - tr_x0));   // 홈통 끝 (코어 축에서). 물이 여기서 물받이 머리의 가운데 물길로 떨어진다
div_end = 286 * k;   // 칸막이 끝. 이 너머 바깥 끝에서 물길이 양쪽 칸으로 열린다
gate_x = 246 * k;    // 마개 자리 (창 아래, 손이 닿는다)
sp_y   = [max(ch_hw + tw + 0.5, 10.5 * k), max(ch_hw + tw + 6.5, 22 * k)];   // 넘친 물 주둥이 (|y|)
sp_r   = Rc + 1.5;   // 주둥이 끝 (코어 축에서). 받침 링 홈통 위
sp_h   = max(5, 8 * k);      // 주둥이 옆벽 높이 (바닥 위)
// 배수 (맨 아래 마디)
sump_z = 66 * k;     // 집수 바닥(원뿔)이 코어 벽 안쪽과 만나는 높이 = 배수 관 바닥
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
module core(z0 = -Hf / 2, base = false) {
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
                if (!base) for (a = [0, 90, 180, 270]) rotate(a) chute();
                else rotate(45) translate([0, 0, sump_z]) hull() {   // 배수 관 꽂는 자리 (아랫면 45°)
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
            for (a = [0, 90, 180, 270]) rotate(a) {
                chute_channel();                                       // 팔로 나가는 구멍과 홈통 물길
                chute_drip();
                for (sg = [-1, 1]) rotate(sg * gut_a)                   // 받침 링 홈통에서 코어 속으로 돌아가는 구멍 (위는 45° 뾰족)
                    translate([Ri - 1, 0, heel_z[1]]) rotate([90, 0, 90]) linear_extrude(wc + 2)
                        polygon([[-gut_w / 2, 0], [gut_w / 2, 0], [gut_w / 2, gut_h], [0, gut_h + gut_w / 2], [-gut_w / 2, gut_h]]);
            }
        } else rotate(45) translate([0, 0, sump_z]) duct_prism(dk_w + 0.2, Ri - 1, Rc + 7);   // 배수 관 구멍
    }
    difference() {                        // 받이 지붕 (가운데 마디) / 집수 바닥 (맨 아래 마디)
        roof_cone(base ? sump_z : roof_z);
        if (base) rotate(45) translate([0, 0, sump_z]) duct_prism(dk_w + 0.2, Rc - wc - 1, Rc + 7);
    }
}

// ---------- 물받이 (쓰는 좌표 = 팔 좌표, +x 팔 안) ----------
// 몸통 단면은 바닥 반너비 tr_b, 옆벽 45° 인 사다리꼴. 머리(코어 쪽)는 발꿈치 위로 바닥이 얕다.
// 칸: 가운데 물길(|y| < ch_hw) 과 양쪽 칸. 홈통 물이 머리의 물길로 떨어져 바깥 끝까지 가서 양쪽 칸으로 나뉘고,
//     양쪽 칸을 거슬러 와 머리 앞 넘침 둑(lv_main)을 넘어 머리 양옆 골로, 다시 주둥이로 나간다.
// 마개(gate)를 물길에 끼우면 물길이 머리 칸막이(lv_by)를 넘쳐 바로 골로 가므로, 이 팔은 윗물을 받지 않는다.
// 출력: 한쪽 옆벽을 판에 대고 45° 로 눕힌다 (part = "tray"). 모든 면이 45° 안쪽이라 서포트가 없다.
function trap(zb, top = tr_rim + 10) = [[-tr_b - (zb - tr_zb), zb], [tr_b + (zb - tr_zb), zb],
                                        [tr_b + (top - tr_zb), top], [-tr_b - (top - tr_zb), top]];
module xprism(poly, x0, x1) { translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) polygon(poly); }
module xprism_off(poly, d, x0, x1) { translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) offset(delta = d) polygon(poly); }
module xbox(x, y, z) { translate([x[0], y[0], z[0]]) cube([x[1] - x[0], y[1] - y[0], z[1] - z[0]]); }
module tray() {
    fl_h = tr_zh + tw;                   // 머리 안 바닥
    fl_m = tr_zb + tw;                   // 몸통 안 바닥
    yo = tr_b + (tr_rim - tr_zb) + 2;    // 바깥 반너비보다 넉넉히
    intersection() {
        union() {
            difference() {
                union() {
                    xprism(trap(tr_zh), tr_x[0], tr_head + 0.01);
                    xprism(trap(tr_zb), tr_head, tr_x[1]);
                }
                // 속: 머리, 몸통 (벽 tw)
                xprism_off(trap(tr_zh), -tw, tr_x[0] + tw, tr_head + tw + 0.01);
                xprism_off(trap(tr_zb), -tw, tr_head + tw, tr_x[1] - tw);
            }
            // 칸막이 (가운데 물길 양옆): 머리는 lv_by, 몸통은 lv_div 까지
            for (sg = [-1, 1]) {
                xbox([tr_x[0], tr_head + tw], sg > 0 ? [ch_hw, ch_hw + tw] : [-ch_hw - tw, -ch_hw], [tr_zb, lv_by]);
                xbox([tr_head, div_end], sg > 0 ? [ch_hw, ch_hw + tw] : [-ch_hw - tw, -ch_hw], [tr_zb, lv_div]);
                // 마개 기둥 (칸막이를 두껍게, 끝은 45°)
                hull() {
                    xbox([gate_x - 4, gate_x + 4], sg > 0 ? [ch_hw, ch_hw + 4] : [-ch_hw - 4, -ch_hw], [tr_zb, lv_div]);
                    xbox([gate_x - 6.4, gate_x + 6.4], sg > 0 ? [ch_hw, ch_hw + tw] : [-ch_hw - tw, -ch_hw], [tr_zb, lv_div]);
                }
                // 넘침 둑: 머리와 몸통 경계, 양쪽 칸 앞
                xbox([tr_head, tr_head + tw], sg > 0 ? [ch_hw, yo] : [-yo, -ch_hw], [tr_zb, lv_main]);
            }
        }
        // 바깥 모양 안으로 자르고, 위는 테두리까지
        union() {
            xprism(trap(tr_zh, tr_rim), tr_x[0], tr_head + 0.01);
            xprism(trap(tr_zb, tr_rim), tr_head, tr_x[1]);
        }
    }
    // 주둥이 (머리 코어 쪽 벽을 뚫고 받침 링 홈통 위로)
    for (sg = [-1, 1]) difference() {
        intersection() {
            xbox([0, tr_x[0] + tw], sg > 0 ? [sp_y[0] - tw, sp_y[1] + tw] : [-sp_y[1] - tw, -sp_y[0] + tw], [tr_zh, fl_h + sp_h]);
            difference() { cylinder(h = 400, r = 400, center = true); cylinder(h = 400, r = sp_r, center = true); }
        }
    }
}
module tray_cut() {             // 주둥이 물길 (머리 코어 쪽 벽까지 뚫는다) + 주둥이 아래 물끊기 홈 + 마개 홈
    for (sg = [-1, 1]) {
        intersection() {
            difference() { cylinder(h = 400, r = sp_r + 2.2, center = true); cylinder(h = 400, r = sp_r + 1.2, center = true); }
            xbox([0, tr_x[0]], sg > 0 ? [sp_y[0] - tw - 1, sp_y[1] + tw + 1] : [-sp_y[1] - tw - 1, -sp_y[0] + tw + 1],
                 [tr_zh - 0.5, tr_zh + 0.6]);
        }
        xbox([0, tr_x[0] + tw + 0.5], sg > 0 ? [sp_y[0], sp_y[1]] : [-sp_y[1], -sp_y[0]], [tr_zh + tw, tr_zh + tw + sp_h + 1]);
        xbox([gate_x - 1.2, gate_x + 1.2], sg > 0 ? [ch_hw - 0.01, ch_hw + 2] : [-ch_hw - 2, -ch_hw + 0.01],
             [tr_zb + tw - 0.01, lv_div + 1]);
    }
}
module tray_full() { difference() { tray(); tray_cut(); } }

// 마개: 가운데 물길을 막는 판 + 창 쪽으로 올라오는 손잡이. 판에 눕혀 뽑는다
module gate() {
    t = 2.0; c = 0.3;
    hy = ch_hw + 2 - c;
    z0 = tr_zb + tw + c;
    translate([gate_x - t / 2, 0, 0]) rotate([90, 0, 90]) linear_extrude(t) difference() {
        union() {
            translate([-hy, z0]) square([2 * hy, lv_div - z0]);
            translate([-max(2, 3 * k), z0]) square([2 * max(2, 3 * k), 40 * k - z0]);
            translate([-8 * k, 28 * k]) square([16 * k, 14 * k]);
        }
        translate([0, 35 * k]) circle(r = 4 * k, $fn = 32);
    }
}

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
    core(base ? -R : -Hf / 2, base);
    for (a = [0, 90, 180, 270]) rotate(a) arm();
}
module water_set(base = false) {
    for (a = [0, 90, 180, 270]) rotate(a) { tray_full(); if (!base) gate(); }
    if (base) rotate(45) translate([0, 0, sump_z]) { valve_body(); translate([vx, 0, 0]) valve_plug(); }
}

if (part == "floor") translate([0, 0, R]) floor_set(true);
else if (part == "floor_water") translate([0, 0, R]) water_set(true);
else if (part == "floor_mid") floor_set();
else if (part == "floor_mid_water") water_set();
else if (part == "tower") {      // 맨 아래 층 + 둘째 층, 물 부품까지
    translate([0, 0, R]) {
        floor_set(true); water_set(true);
        translate([0, 0, Hf]) rotate(twist) { floor_set(); water_set(); }
    }
}
else if (part == "arm")   translate([0, 0, reach]) rotate([0, 90, 0]) arm();     // 바깥 끝이 바닥, 코어 쪽이 위
else if (part == "core")  translate([0, 0, -core_low()]) core();      // 아래 꽂이 끝이 바닥
else if (part == "core_base") translate([0, 0, R]) core(-R, true);
else if (part == "core_joint") {  // 쌓기 이음 시험: 코어 아래 끝 어깨·꽂이 (꽂는 쪽) + 위 끝 30 mm (받는 쪽)
    zb = -Hf / 2 + (wc - ch + 0.1);
    translate([-Rc - 8, 0, 0]) intersection() { translate([0, 0, -core_low()]) core(); cylinder(h = zb + 25 - core_low(), r = 2 * Rc); }
    translate([Rc + 8, 0, 0]) intersection() { translate([0, 0, -(Hf / 2 - 30)]) core(); cylinder(h = 31, r = 2 * Rc); }
}
else if (part == "tray") translate([0, 0, (tr_b - tr_zb) / sqrt(2)]) rotate([45, 0, 0]) tray_full();
else if (part == "gate") translate([0, 0, 1]) rotate([0, -90, 0]) translate([-gate_x, 0, 0]) gate();
else if (part == "valve_body") translate([0, 0, dk_w]) valve_body();
else if (part == "valve_plug") translate([0, 0, 16 + 6]) rotate([180, 0, 0]) valve_plug();

echo(str("DIMS cross_span=", 2 * reach, " arm_D=", D, " core_D=", 2 * Rc, " floor_h=", Hf,
         " arm_print_h=", reach - (Rc + gapc)));
