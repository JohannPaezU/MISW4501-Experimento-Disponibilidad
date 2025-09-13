from requests import get
from colored import fg, attr
import threading
import time
import os

url_base = os.getenv("MONITOR_URL", "http://127.0.0.1:5000/monitor")
enqueue_url = f"{url_base}/orders/status/check"
status_url = f"{url_base}/orders/status"
threads_count = int(os.getenv("THREADS_COUNT", "50"))
thread_requests = int(os.getenv("REQUESTS_PER_THREAD", "10"))
total_requests = 0
enqueue_errors = 0
availability_errors = 0
lock = threading.Lock()


def do_monitor_request(requests):
    global total_requests, enqueue_errors, availability_errors
    for _ in range(requests):
        ini = time.time()
        
        try:
            r = get(enqueue_url, timeout=10)
            enqueue_status = r.status_code
        except Exception as e:
            enqueue_status = 500
        
        time.sleep(0.5)
        
        try:
            r_status = get(status_url, timeout=10)
            status_code = r_status.status_code
            response_data = r_status.json() if r_status.headers.get('content-type', '').startswith('application/json') else {}
        except Exception as e:
            status_code = 500
            response_data = {'error_details': str(e)}
        
        fin = time.time()
        total_time = round(fin - ini, 3)
        
        with lock:
            total_requests += 1
            current = total_requests
            
            if enqueue_status != 200:
                enqueue_errors += 1
            
            if status_code == 503:
                availability_errors += 1
        
        real_availability = response_data.get('real_availability_percentage', 'N/A')
        total_records = response_data.get('total_records', 'N/A')
        error_details = response_data.get('error_details', '')
        
        response = f"Solicitud {current}: Encolar({enqueue_status}) -> Estado({status_code}) | Disponibilidad: {real_availability}% | Registros: {total_records} | {total_time}s"
        
        if enqueue_status != 200:
            print(fg(196) + f"[ERROR ENCOLAR] {response}" + attr(0))
        elif status_code == 503:
            print(fg(226) + f"[BAJA DISPONIBILIDAD] {response}" + attr(0))
        elif status_code == 200:
            print(fg(46) + f"[OK] {response}" + attr(0))
        else:
            error_msg = f" | Error: {error_details}" if error_details else ""
            print(fg(196) + f"[ERROR ESTADO {status_code}] {response}{error_msg}" + attr(0))
            
        time.sleep(0.1)


if __name__ == '__main__':
    print(f"Iniciando prueba con {threads_count} hilos, {thread_requests} solicitudes por hilo")
    print(f"URL de encolamiento: {enqueue_url}")
    print(f"URL de estado: {status_url}")
    print("-" * 80)
    
    threads = []
    start_time = time.time()
    
    for i in range(threads_count):
        thread = threading.Thread(target=lambda: do_monitor_request(thread_requests))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print("\nEsperando procesamiento final...")
    time.sleep(2)
    
    try:
        final_response = get(status_url, timeout=5)
        final_data = final_response.json() if final_response.headers.get('content-type', '').startswith('application/json') else {}
        final_total_records = final_data.get('total_records', 0)
        final_real_availability = final_data.get('real_availability_percentage', 0)
        final_configured_availability = final_data.get('expected_availability_percentage', 90)
    except Exception as e:
        print(f"Error obteniendo estado final: {e}")
        final_total_records = 0
        final_real_availability = 0
        final_configured_availability = 90
    
    total_time = round(time.time() - start_time, 2)
    expected_requests = threads_count * thread_requests
    
    print("-" * 80)
    print("RESULTADOS DE LA PRUEBA:")
    print(f"Hilos: {threads_count}")
    print(f"Solicitudes por hilo: {thread_requests}")
    print(f"Total solicitudes esperadas: {expected_requests}")
    print(f"Solicitudes enviadas: {total_requests}")
    print(f"Registros procesados: {final_total_records}")
    print(f"Errores de encolamiento: {enqueue_errors}")
    print(f"Errores de disponibilidad (503): {availability_errors}")
    print(f"Verificaciones de disponibilidad exitosas: {total_requests - enqueue_errors - availability_errors}")
    
    processing_success_rate = round((final_total_records / expected_requests) * 100, 2) if expected_requests > 0 else 0
    
    print("-" * 80)
    print("ANÁLISIS DE DISPONIBILIDAD:")
    print(f"Disponibilidad real final: {final_real_availability}%")
    print(f"Umbral de disponibilidad configurado: {final_configured_availability}%")
    print(f"Tasa de éxito de procesamiento: {processing_success_rate}%")
    
    system_available = final_real_availability >= final_configured_availability
    
    if processing_success_rate < 95:
        print(fg(196) + "ADVERTENCIA: ¡Algunas solicitudes pueden haberse perdido o no procesado correctamente!" + attr(0))
    
    if system_available:
        print(fg(46) + f"SISTEMA DISPONIBLE: Disponibilidad real ({final_real_availability}%) >= Umbral ({final_configured_availability}%)" + attr(0))
    else:
        print(fg(196) + f"SISTEMA NO DISPONIBLE: Disponibilidad real ({final_real_availability}%) < Umbral ({final_configured_availability}%)" + attr(0))
    
    print(f"Tiempo total transcurrido: {total_time}s")
