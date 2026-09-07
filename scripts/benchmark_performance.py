"""
Benchmark script measuring first-run vs subsequent-run latency for:
1. Short text: '대한민국의 경제는 빠르게 발전하였다.'
2. Long text: ~2,000 characters of authentic Korean editorial/academic text.
"""

import time
import httpx

BASE_URL = 'http://127.0.0.1:8000'

SHORT_TEXT = "대한민국의 경제는 빠르게 발전하였다."

# Standard Korean expository text (~2000 chars) covering history, economy, science, and education
PARAGRAPHS = [
    "대한민국의 경제는 지난 반세기 동안 전례 없는 속도로 발전하였다. 농업 중심의 빈곤국에서 출발하여 첨단 정보통신기술과 제조업을 선도하는 산업 강국으로 도약한 대한민국의 발전 모델은 세계 여러 개발도상국에 깊은 영감을 주고 있다.",
    "특히 과학기술 혁신과 교육에 대한 국가적 투자는 경제 성장의 핵심적인 원동력이었다. 연구원들과 기업인들의 헌신적인 노력, 그리고 정부의 체계적인 정책 지원이 결합되어 반도체, 자동차, 조선, 화학 등 주요 산업 분야에서 세계적인 경쟁력을 확보할 수 있었다.",
    "국제화는 한국 사회의 모든 영역에서 거스를 수 없는 거대한 흐름이 되었다. 문화적 다양성을 존중하고 다문화 사회로의 이행을 능동적으로 수용하는 태도는 21세기 대한민국의 지속 가능한 번영을 위해 필수적인 과제로 대두되고 있다.",
    "새로운 세대는 정보화 시대의 혜택 속에서 성장하며 창의적 사고와 협력적 문제 해결 능력을 기르고 있다. 스마트폰과 컴퓨터, 인공지능 기술의 발전은 일상생활뿐만 아니라 교육 환경과 노동 시장에도 혁명적인 변화를 가져왔다.",
    "그러나 급격한 경제 성장과 사회 구조의 변동은 소득 불평등의 심화, 환경 오염, 급속한 저출산 및 고령화와 같은 심각한 사회적 부작용을 수반하였다. 이러한 난제들을 해결하기 위해서는 정부, 기업, 시민사회가 함께 참여하는 포용적 복지 정책과 지속 가능한 경제 체제의 구축이 절실히 요구된다.",
    "평화를 위한 남북 화해와 동북아시아의 평화 정착 역시 한민족의 장기적인 번영을 위해 결코 포기할 수 없는 중대한 목표이다. 국제 평화와 협력을 증진하기 위한 외교적 노력은 지속되어야 하며, 국민적 합의를 바탕으로 흔들림 없이 추진되어야 한다.",
]

# Assemble into ~2,000 chars
sample_text = "\n\n".join(PARAGRAPHS)
while len(sample_text) < 2000:
    sample_text += "\n\n" + "\n\n".join(PARAGRAPHS)
LONG_TEXT = sample_text[:2050]

def benchmark():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    print("=" * 60)
    print("HANJA CONVERTER PERFORMANCE BENCHMARK (PORT 8000)")
    print("=" * 60)
    
    # 1. Version and stats verification
    v_resp = client.get('/api/version').json()
    print(f"Code Version:        {v_resp.get('code_version')}")
    print(f"API Schema Version:  {v_resp.get('api_schema_version')}")
    print(f"Data Version:        {v_resp.get('data_version')}")
    print(f"Total Entries:       {v_resp.get('db_stats', {}).get('total_entries')}")
    print(f"Total Senses:        {v_resp.get('db_stats', {}).get('total_senses')}")
    print(f"Total Examples:      {v_resp.get('db_stats', {}).get('total_examples')}")
    print("-" * 60)

    # 2. Short Text Benchmark
    print(f"\n--- 1. Short Text Benchmark ({len(SHORT_TEXT)} chars) ---")
    print(f"Text: '{SHORT_TEXT}'")
    
    # Cold / First run
    t0 = time.perf_counter()
    resp_short_first = client.post('/api/convert', json={'text': SHORT_TEXT}).json()
    t_short_first = (time.perf_counter() - t0) * 1000.0
    mixed_short = "".join(s['display_text'] for s in resp_short_first['segments'])
    server_ms_first = resp_short_first.get('processing_time_ms', 0.0)
    
    print(f"Result:              '{mixed_short}'")
    print(f"First request:       Roundtrip: {t_short_first:.2f} ms | Server: {server_ms_first:.2f} ms")
    
    # Subsequent runs (5 iterations)
    subsequent_short = []
    subsequent_server_short = []
    for i in range(5):
        t0 = time.perf_counter()
        r = client.post('/api/convert', json={'text': SHORT_TEXT}).json()
        subsequent_short.append((time.perf_counter() - t0) * 1000.0)
        subsequent_server_short.append(r.get('processing_time_ms', 0.0))
        
    avg_short = sum(subsequent_short) / len(subsequent_short)
    avg_server_short = sum(subsequent_server_short) / len(subsequent_server_short)
    print(f"Subsequent (avg 5):  Roundtrip: {avg_short:.2f} ms | Server: {avg_server_short:.2f} ms")
    print(f"Min / Max roundtrip: {min(subsequent_short):.2f} ms / {max(subsequent_short):.2f} ms")

    # 3. Long Text Benchmark (~2,000 chars)
    print(f"\n--- 2. Long Text Benchmark ({len(LONG_TEXT)} chars) ---")
    
    # Cold / First run
    t0 = time.perf_counter()
    resp_long_first = client.post('/api/convert', json={'text': LONG_TEXT}).json()
    t_long_first = (time.perf_counter() - t0) * 1000.0
    server_ms_long_first = resp_long_first.get('processing_time_ms', 0.0)
    seg_count = len(resp_long_first['segments'])
    converted_count = sum(1 for s in resp_long_first['segments'] if s['status'] == 'converted')
    
    print(f"Segments produced:   {seg_count} segments (Converted: {converted_count})")
    print(f"First request:       Roundtrip: {t_long_first:.2f} ms | Server: {server_ms_long_first:.2f} ms")

    # Subsequent runs (5 iterations)
    subsequent_long = []
    subsequent_server_long = []
    for i in range(5):
        t0 = time.perf_counter()
        r = client.post('/api/convert', json={'text': LONG_TEXT}).json()
        subsequent_long.append((time.perf_counter() - t0) * 1000.0)
        subsequent_server_long.append(r.get('processing_time_ms', 0.0))
        
    avg_long = sum(subsequent_long) / len(subsequent_long)
    avg_server_long = sum(subsequent_server_long) / len(subsequent_server_long)
    print(f"Subsequent (avg 5):  Roundtrip: {avg_long:.2f} ms | Server: {avg_server_long:.2f} ms")
    print(f"Min / Max roundtrip: {min(subsequent_long):.2f} ms / {max(subsequent_long):.2f} ms")
    
    # 4. Origin Verification
    print("\n--- 3. Single-Pass Origin Verification ---")
    has_origin = sum(1 for s in resp_long_first['segments'] if s.get('origin'))
    print(f"Segments with pre-attached origin: {has_origin} (Zero client-side roundtrips required!)")

    print("=" * 60)
    print("BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    benchmark()
