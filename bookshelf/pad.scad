// 책장 칸 바닥 TPU 패드
// 칸 너비와 상관없이 크기를 먼저 정한다. 칸을 설계할 때 바닥 모서리에 이 패드가 들어가는 홈을 낸다:
//   홈 지름 = pad_d + 0.4, 홈 깊이 = pad_h - pad_out  (패드가 pad_out 만큼 튀어나와 바닥에 닿는다)
// part = "pad"   패드 하나
//        "set"   패드 n 개 (한 판)
// openscad -o stl/pad_x12.stl -D 'part="set"' pad.scad

pad_d   = 20;     // 패드 지름
pad_h   = 3;      // 패드 두께
pad_out = 1.5;    // 칸 바닥 밖으로 나오는 높이
ch      = 0.6;    // 위 모서리 모따기 (홈에 넣기 쉽게)
n       = 12;     // 한 판에 뽑을 개수
gap     = 6;
part    = "set";
$fn     = 96;

module pad() {
    cylinder(h = pad_h - ch, d = pad_d);
    translate([0, 0, pad_h - ch]) cylinder(h = ch, d1 = pad_d, d2 = pad_d - 2 * ch);
}

if (part == "pad") pad();
else if (part == "set") {
    cols = 4;
    for (i = [0 : n - 1]) translate([(i % cols) * (pad_d + gap), floor(i / cols) * (pad_d + gap), 0]) pad();
}

echo(str("PAD d=", pad_d, " h=", pad_h, " recess d=", pad_d + 0.4, " depth=", pad_h - pad_out));
