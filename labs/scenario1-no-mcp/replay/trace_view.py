"""トレース JSON を、1ステップずつ再生できる1枚の HTML にする。

  （ラボ直下から実行する）
  python3 replay/trace_view.py traces/A.json                      # → traces/A.html
  python3 replay/trace_view.py traces/A.json traces/B.json -o cmp.html   # 複数を切り替えて見比べる

テンプレートは replay/trace_view.template.html。外部ライブラリは使わず、データは HTML に埋め込む
（file:// で開いても fetch が要らないように）。
"""
import argparse, json, pathlib

TEMPLATE = pathlib.Path(__file__).with_name("trace_view.template.html")


def render(traces, out_path):
    data = json.dumps(traces, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__TRACES__*/[]", data)
    out_path = pathlib.Path(out_path)
    out_path.write_text(html)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    traces = [json.loads(pathlib.Path(p).read_text()) for p in a.traces]
    out = a.out or pathlib.Path(a.traces[0]).with_suffix(".html")
    print(render(traces, out))


if __name__ == "__main__":
    main()
