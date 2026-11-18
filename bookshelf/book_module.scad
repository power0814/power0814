// 책 한 권에 맞춰 뽑는 책장 모듈 (파라메트릭)
// ------------------------------------------------------------
// 책 치수 세 개(높이, 너비, 두께)를 넣으면 그 책만을 위한 칸이 나온다.
//  - 바깥 치수는 격자(grid)에 맞춰 올림 → 어떤 모듈끼리도 쌓이고 핀으로 맞물린다.
//  - 안쪽 공간은 책에 딱 맞춤 → 격자와 책의 차이는 측벽·뒷벽·바닥판 두께가 흡수한다.
//  - 측벽은 한쪽만 있다(C자 단면). 반대쪽 윗판 모서리는 책이 받친다:
//    책이 빠지면 칸이 약해지는, "책이 네 번째 벽"인 구조.
//  - 책 밑에는 받침(shoe)과 쐐기(wedge)가 겹쳐 들어간다(쌍쐐기).
//    쐐기를 빼면 받침이 drop 만큼 내려가 하중이 풀리고, 책은 받침째 빠진다.
//
// 좌표: x = 책 두께 방향(왼→오), y = 깊이(0 = 앞면/책등, +y = 벽 쪽), z = 위.  단위 mm.
// 출력: 모듈은 닫힌 측벽(x = 0 면)을 바닥에 눕혀 뽑으면 지지대가 필요 없다.
// OpenSCAD 2021.01 이상.

/* [책 치수] */
book_h = 240;        // 높이 (세웠을 때)
book_w = 165;        // 너비 (= 칸 깊이)
book_t = 22;         // 두께 (= 책등 폭)
idx    = "07";       // 앞면 각인 (번호)
note   = "2026.11";  // 측면 각인 (입고일)
lay    = false;      // 눕혀 꽂기: 책등은 앞, 두께가 위아래 (가로형·큰 판형)

/* [출력할 부품] */
part = "preview";    // [preview, module, shoe, wedge, pin]

/* [시스템 치수] */
grid        = 10;    // 바깥 치수 격자
side_min    = 3;     // 닫힌 측벽 최소 두께
back_min    = 2.4;   // 뒷벽 최소 두께
plinth_min  = 6;     // 바닥판 최소 두께 (번호 각인 자리)
top_t       = 4;     // 윗판 두께
clear_t     = 0.6;   // 두께 방향 여유 (한쪽)
clear_w     = 1.0;   // 깊이 방향 여유 (뒤쪽)
pad         = 1.5;   // 윗판 아래 코르크 패드 두께
lift        = 10.5;  // 받침+쐐기 높이 (쐐기를 끝까지 넣었을 때)
drop        = 2;     // 쐐기를 빼면 받침이 내려가는 높이
wedge_front = 8;     // 쐐기 앞쪽 높이 (뒤쪽은 drop)
shoe_tab    = 8;     // 받침 손잡이가 앞으로 나온 길이
wedge_tab   = 16;    // 쐐기 손잡이가 앞으로 나온 길이
rail        = 12;    // 측벽 창 둘레 테두리 폭
pin_d       = 4;     // 연결 핀 지름
pin_depth   = 3;     // 핀 구멍 깊이 (판마다)
pin_rows    = [20, 100];        // 핀 줄: 벽에서 떨어진 거리
bed         = [330, 320, 325];  // 프린터 출력 범위 (A2L)

font = "DejaVu Sans:style=Bold";
$fn = 32;

// ------------------------------------------------------------
// 치수 계산
function ceilg(v) = grid * ceil(v / grid - 1e-9);

// [X, Y, Z, 측벽 sx, 뒷벽 by, 바닥판 pz, 공간 폭 cav]
function dims(h, w, t) =
    let(cav = t + 2 * clear_t,
        X   = ceilg(side_min + cav),
        Y   = ceilg(back_min + clear_w + w),
        Z   = ceilg(plinth_min + lift + h + pad + top_t))
    [X, Y, Z, X - cav, Y - w - clear_w, Z - (lift + h + pad + top_t), cav];

function wedge_w(cav) = max(5, min(14, cav - 6));

// 눕혀 출력할 때(측벽이 바닥): 바닥 면적 Y×Z, 높이 X
function fits_bed(d) =
    let(a = max(d[1], d[2]), b = min(d[1], d[2]))
    a <= max(bed[0], bed[1]) && b <= min(bed[0], bed[1]) && d[0] <= bed[2];

// ------------------------------------------------------------
// 모듈 본체
// h, w, t는 칸 기준 (h = 위아래, t = 좌우). 눕힌 책은 호출할 때 h와 t를 바꿔 넣는다.
module shelf_module(h, w, t, idx = "", note = "", dimstr = undef) {
    d = dims(h, w, t);
    X = d[0]; Y = d[1]; Z = d[2]; sx = d[3]; by = d[4]; pz = d[5];
    difference() {
        union() {
            cube([X, Y, pz]);                              // 바닥판
            translate([0, 0, Z - top_t]) cube([X, Y, top_t]);  // 윗판
            translate([0, Y - by, 0]) cube([X, by, Z]);        // 뒷벽
            side_frame(Y, Z, sx, by, pz);                      // 닫힌 측벽 (x = 0 쪽만)
        }
        pin_holes(X, Y, Z);
        keyhole(X, Y, Z, by);
        labels(X, Y, pz, is_undef(dimstr) ? str(h, "x", w, "x", t) : dimstr, idx, note);
    }
}

// 측벽: 테두리만 남긴 틀. 창으로 책 표지가 보인다.
module side_frame(Y, Z, sx, by, pz) {
    wy = Y - by - 2 * rail;
    wz = Z - top_t - pz - 2 * rail;
    rotate([90, 0, 90]) linear_extrude(sx)
        difference() {
            square([Y, Z]);
            if (wy > 12 && wz > 12)
                translate([rail, pz + rail])
                    offset(r = 5) offset(delta = -5) square([wy, wz]);
        }
}

// 위아래 모듈을 잇는 핀 구멍. 격자 위에 있어서 어떤 모듈끼리도 맞는다.
module pin_holes(X, Y, Z) {
    for (x = [grid / 2 : grid : X - 1], r = pin_rows)
        if (Y - r > 8)
            translate([x, Y - r, 0]) {
                translate([0, 0, -1])            cylinder(d = pin_d + 0.2, h = pin_depth + 1);
                translate([0, 0, Z - pin_depth]) cylinder(d = pin_d + 0.2, h = pin_depth + 1);
            }
}

// 벽 고정용 열쇠구멍 (뒷벽)
module keyhole(X, Y, Z, by) {
    translate([X / 2, Y - by - 1, Z - top_t - 16])
        rotate([-90, 0, 0])
            hull() {
                cylinder(d = 4.5, h = by + 2);
                translate([0, -7, 0]) cylinder(d = 4.5, h = by + 2);
            }
    translate([X / 2, Y - by - 1, Z - top_t - 16])
        rotate([-90, 0, 0]) cylinder(d = min(8.5, X - 6), h = by + 2);
}

// 앞면: 번호 / 닫힌 측면: 번호·입고일·책 치수
module labels(X, Y, pz, dimstr, idx, note) {
    if (pz >= 6 && X >= 14)
        translate([X / 2, 0.6, pz / 2]) rotate([90, 0, 0]) linear_extrude(1)
            text(idx, size = min(pz - 2.5, (X - 4) / 1.4, 7), font = font,
                 halign = "center", valign = "center");
    translate([0.6, Y / 2, pz / 2]) rotate([90, 0, -90]) linear_extrude(1)
        text(str(idx, "  ", note, "  ", dimstr),
             size = min(pz - 2.5, 4), font = font, halign = "center", valign = "center");
}

// ------------------------------------------------------------
// 받침과 쐐기
module wedge_solid(h, w, t, grow = 0) {
    d = dims(h, w, t); sx = d[3]; pz = d[5]; cav = d[6];
    kw = wedge_w(cav) + 2 * grow;
    x0 = sx + cav / 2 - kw / 2;
    union() {
        hull() {   // 경사부: 앞 wedge_front → 뒤 drop
            translate([x0, 0, pz])      cube([kw, 0.01, wedge_front]);
            translate([x0, w - 10, pz]) cube([kw, 0.01, drop]);
        }
        translate([x0, -wedge_tab, pz]) cube([kw, wedge_tab + 0.01, wedge_front]);  // 손잡이
    }
}

module wedge(h, w, t) {
    d = dims(h, w, t); sx = d[3]; pz = d[5]; cav = d[6];
    difference() {
        wedge_solid(h, w, t);
        translate([sx + cav / 2, -wedge_tab + 5, pz - 1]) cylinder(d = 4, h = wedge_front + 2);
    }
}

// 받침: 넓은 받침(눕힌 책)은 테두리·가운데 띠·가로 리브만 남기고 비운다
module shoe(h, w, t) {
    d = dims(h, w, t); sx = d[3]; pz = d[5]; cav = d[6];
    x0 = sx + 0.3; x1 = sx + cav - 0.3;
    kw = wedge_w(cav); c0 = sx + cav / 2 - kw / 2 - 6; c1 = sx + cav / 2 + kw / 2 + 6;
    nseg = max(1, round((w - 16) / 70));
    seg = (w - 16 - (nseg - 1) * 8) / nseg;
    difference() {
        translate([x0, -shoe_tab, pz + drop]) cube([x1 - x0, w + shoe_tab, lift - drop]);
        wedge_solid(h, w, t, grow = 0.3);
        for (p = [[x0 + 8, c0], [c1, x1 - 8]], i = [0 : nseg - 1])
            if (p[1] - p[0] >= 15)
                translate([p[0], 8 + i * (seg + 8), pz]) cube([p[1] - p[0], seg, lift + 1]);
    }
}

module pin() { cylinder(d = pin_d, h = 2 * pin_depth - 0.4); }

// 미리보기: 모듈 + 받침 + 쐐기 + 패드 + 책 (h, w, t는 칸 기준)
module preview(h, w, t, idx = "", note = "", book_color = "#3E5C76", dimstr = undef) {
    d = dims(h, w, t); X = d[0]; Z = d[2]; sx = d[3]; pz = d[5]; cav = d[6];
    color("#ECE7DF") shelf_module(h, w, t, idx, note, dimstr);
    color("#8E8780") shoe(h, w, t);
    color("#C9663D") wedge(h, w, t);
    color("#B48A5A") translate([sx, 0, Z - top_t - pad]) cube([cav, w, pad]);
    color(book_color) translate([sx + clear_t, 0, pz + lift]) cube([t, w, h]);
}

// ------------------------------------------------------------
// 칸 기준 치수: 눕히면 책 두께가 위아래, 책 높이가 좌우가 된다
CH = lay ? book_t : book_h;
CT = lay ? book_h : book_t;
DS = str(book_h, "x", book_w, "x", book_t, lay ? " L" : "");

D = dims(CH, book_w, CT);
echo(str("DIMS ", D[0], " ", D[1], " ", D[2], " ", D[3], " ", D[4], " ", D[5], " ", D[6]));
echo(str("FITS_BED ", fits_bed(D)));

if      (part == "preview") preview(CH, book_w, CT, idx, note, dimstr = DS);
else if (part == "module")  shelf_module(CH, book_w, CT, idx, note, DS);
else if (part == "shoe")    shoe(CH, book_w, CT);
else if (part == "wedge")   wedge(CH, book_w, CT);
else if (part == "pin")     pin();
