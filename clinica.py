import datetime
import json
import re

import requests
import bs4

s = requests.Session()
res = s.get("https://www.clinicasantamaria.cl/reserva-horas/ficha-especialista/index/1111120204")
soup = bs4.BeautifulSoup(res.content, "lxml")
request_data = {}
for inp in soup.find(id='buscadorFormulario').find_all('input'):
    request_data[inp.get("name")] = inp.get("value", "")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
request_data["form.codigoSucursal"] = "0"
request_data['form.rut'] = "19267686-K"
res = s.post("https://www.clinicasantamaria.cl/reserva-horas/reserva/buscadorTerminos", data=request_data,
             headers=headers)

print(res.json())
res = s.post("https://www.clinicasantamaria.cl/reserva-horas/reserva/busquedaCategoria", data=request_data,
             headers=headers)
print(res.json())

res = s.get("https://www.clinicasantamaria.cl/reserva-horas/ficha-especialista/index/1111120204")
soup = bs4.BeautifulSoup(res.content, "lxml")

script = soup.find(text=re.compile("var modeloObtenido"))
script2 = '\n'.join(' '.join(script.string.splitlines()).split('var'))

modeloSesionObtenido = json.loads(re.search("var modeloSesionObtenido = (.*);", res.content.decode()).group(1))
medico = json.loads(re.search("var medico = (.*);", res.content.decode()).group(1))
_proximaFechaDesdeFicha = re.search("var _proximaFechaDesdeFicha = (.*);", res.content.decode()).group(1)[1:-1]

request_data = {}
for inp in soup.find(id='buscadorConcepto').find_all('input'):
    request_data[inp.get("name")] = inp.get("value", "")

especialidad = modeloSesionObtenido["idTipoCategoriaBuscado"] \
    if modeloSesionObtenido["idTipoCategoriaBuscado"] > 0 else medico["subEspecialidades"][0]["id"]
request_data['form.idTipo'] = modeloSesionObtenido["idTipoCategoriaBuscado"]
request_data['form.tipo'] = modeloSesionObtenido["tipoCategoriaBuscado"]
request_data['form.codigoSucursal'] = modeloSesionObtenido["sucursalBuscado"]
request_data['form.buscaTermino'] = modeloSesionObtenido["terminoBuscado"]
request_data['form.sexoEspecialista'] = modeloSesionObtenido["sexoBuscado"]
request_data['form.fecha'] = _proximaFechaDesdeFicha if len(_proximaFechaDesdeFicha) > 0 else modeloSesionObtenido[
    "fechaBuscado"]
request_data['form.identificacionMedico'] = medico["codigo"]
request_data['form.esMensual'] = modeloSesionObtenido["esMensual"]
request_data['form.idEspecialidad'] = especialidad
request_data['form.idMedicoSucursal'] = modeloSesionObtenido["sucursalBuscado"]

res = s.post("https://www.clinicasantamaria.cl/reserva-horas/ficha-especialista/resultadosoptimo", data=request_data,
             headers=headers)
final = res.json()
proximaFechaRaw = final["response"]["medicosPorBusqueda"][0]["ProximaHora"]
proximaFechaMili = int(re.search(r"Date\((.*)\)", proximaFechaRaw).group(1))
proximaFecha = datetime.datetime.fromtimestamp(proximaFechaMili // 1000).isoformat()
print(proximaFecha)
