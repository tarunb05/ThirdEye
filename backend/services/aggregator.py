def aggregate_scans(scans_a: list, scans_b: list, scans_c: list) -> list:
    '''
    Aggregate multi-LLM vulnerability scans using consensus logic.
    '''
    consensus = {}
    
    for vuln in scans_a + scans_b + scans_c:
        key = f\"{vuln['type']}_{vuln['line']}\"
        if key not in consensus:
            consensus[key] = {'count': 0, 'confidences': [], 'data': vuln}
        consensus[key]['count'] += 1
        consensus[key]['confidences'].append(vuln['confidence'])
    
    final_vulns = []
    for key, data in consensus.items():
        count = data['count']
        avg_confidence = sum(data['confidences']) / len(data['confidences'])
        
        if count == 3:
            final_confidence = min(0.95, avg_confidence + 0.15)
        elif count == 2:
            final_confidence = avg_confidence * 0.80
        else:
            final_confidence = avg_confidence * 0.50
        
        if final_confidence > 0.35:
            final_vulns.append({
                **data['data'],
                'final_confidence': final_confidence,
                'consensus_count': count
            })
    
    return final_vulns

def determine_verdict(vulns: list) -> str:
    '''Return GO or NO-GO based on vulnerabilities'''
    critical = [v for v in vulns if v.get('severity') == 'critical' and v.get('final_confidence', 0) > 0.7]
    return 'NO-GO' if critical else 'GO'
