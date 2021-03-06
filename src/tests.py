#!/usr/bin/env python2
# coding: utf-8

import unittest
from sqlite3 import IntegrityError
import tp_api as api

class TestModel(unittest.TestCase):

    def setUp(self):
        # Crear una base en memoria y crear las tablas
        self.connector = api.bd_connector()
        self.connector.connect(bd=':memory:')
        f = open('../db/facultad.sql', 'r')
        self.connector.conn.executescript(f.read())

        # El modelo ahora usa la base en memoria en lugar del archivo facultad.db
        self.model = api.model_test(self.connector)

    ################################################################################
    # Padrón electoral                                                             #
    ################################################################################

    def test_se_crea_una_facultad_por_defecto(self):
        # Al empadronarse un DNI se registra una facultad por defecto
        self.model.empadronar_alumno(123, 'Alumno')

        # Verificar que se haya creado la entrada en la tabla facultad
        self.assertSelectEquals('SELECT id, nombre FROM facultad', (),
                                (1, api.NOMBRE_FACULTAD))

    def test_empadronar_alumno(self):
        dni = 123
        nombre = 'Alumno'

        self.model.empadronar_alumno(dni, nombre)

        # Verificar que se respete la unicidad de DNIs
        with self.assertRaises(IntegrityError):
            self.model.empadronar_alumno(dni, nombre)

        # Verificar que se haya creado la entrada en la tabla empadronado
        self.assertSelectEquals('SELECT nombre, claustro FROM empadronado WHERE dni = ?', (dni,),
                                (nombre, api.CLAUSTRO_ESTUDIANTES))

        # Verificar que se haya creado la entrada en la tabla estudiante
        self.assertSelectIsNotEmpty('SELECT * FROM estudiante WHERE dni = ?', (dni,))

    def test_empadronar_graduado(self):
        dni = 123
        nombre = 'Graduado'

        self.model.empadronar_graduado(dni, nombre)

        # Verificar que se respete la unicidad de DNIs
        with self.assertRaises(IntegrityError):
            self.model.empadronar_graduado(dni, nombre)

        # Verificar que se haya creado la entrada en la tabla empadronado
        self.assertSelectEquals('SELECT nombre, claustro FROM empadronado WHERE dni = ?', (dni,),
                                (nombre, api.CLAUSTRO_GRADUADOS))

        # Verificar que se haya creado la entrada en la tabla graduado
        self.assertSelectEquals('SELECT universidad FROM graduado WHERE dni = ?', (dni,),
                                (api.UBA,))


    def test_empadronar_profesor(self):
        dni = 123
        nombre = 'Profesor'

        self.model.empadronar_profesor(dni, nombre)

        # Verificar que se respete la unicidad de DNIs
        with self.assertRaises(IntegrityError):
            self.model.empadronar_profesor(dni, nombre)

        # Verificar que se haya creado la entrada en la tabla empadronado
        self.assertSelectEquals('SELECT nombre, claustro FROM empadronado WHERE dni = ?', (dni,),
                                (nombre, api.CLAUSTRO_PROFESORES))

        # Verificar que se haya creado la entrada en la tabla profesor
        self.assertSelectEquals('SELECT nacionalidad_universidad, cargo FROM profesor WHERE dni = ?', (dni,),
                                (api.NACIONALIDAD_UNIVERSIDAD_PROFESOR, api.CARGO_PROFESOR_REGULAR))


    ################################################################################
    # Consejo directivo                                                            #
    ################################################################################

    def test_crear_agrupacion_politica(self):
        nombre = u'Agrupación'

        id = self.model.crear_agrupacion_politica(nombre)

        # Verificar que se haya creado la entrada en la tabla agrupacion_politica
        self.assertSelectEquals('SELECT nombre FROM agrupacion_politica WHERE id = ?', (id,), (nombre,))

    def test_registrar_votos_eleccion_consejo_directivo(self):
        nombre = u'Agrupación'
        periodo = 2014
        votos_recibidos = 10

        # Asegurar que se requiera un ID de agrupación política válido
        with self.assertRaises(IntegrityError):
            self.model.registrar_votos_eleccion_consejo_directivo(0, periodo, votos_recibidos)

        id_agrupacion_politica = self.model.crear_agrupacion_politica(nombre)
        self.model.registrar_votos_eleccion_consejo_directivo(id_agrupacion_politica, periodo, votos_recibidos)

        # Asegurar que no se puedan registrar los votos más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_votos_eleccion_consejo_directivo(id_agrupacion_politica, periodo, votos_recibidos)

        # Verificar que exista el período en el calendario electoral
        self.assertSelectIsNotEmpty('SELECT * FROM calendario_electoral WHERE periodo = ?', (periodo,))

        # Verificar que se haya creado la entrada en la tabla agrupacion_politica_se_presenta_durante_calendario_electoral
        self.assertSelectEquals('''SELECT votos_recibidos FROM agrupacion_politica_se_presenta_durante_calendario_electoral
                                   WHERE id_agrupacion_politica = ? AND periodo = ?''', (id_agrupacion_politica, periodo),
                                (votos_recibidos,))

    def test_crear_consejero_directivo_claustro_estudiantes(self):
        self.crear_consejero_directivo(api.CLAUSTRO_ESTUDIANTES)

    def test_crear_consejero_directivo_claustro_graduados(self):
        self.crear_consejero_directivo(api.CLAUSTRO_GRADUADOS)

    def test_crear_consejero_directivo_claustro_graduados(self):
        self.crear_consejero_directivo(api.CLAUSTRO_PROFESORES)

    def crear_consejero_directivo(self, claustro):
        dni = 123
        nombre = 'Consejero'
        nombre_agrupacion_politica = u'Agrupación'
        periodo = 2014

        id_agrupacion_politica = self.model.crear_agrupacion_politica(nombre_agrupacion_politica)

        # Asegurar que un DNI no empadronado no pueda ser consejero directivo
        with self.assertRaises(AssertionError):
            self.model.crear_consejero_directivo(dni, periodo, 0)

        # Empadronar el DNI en el padrón correspondiente
        if claustro == api.CLAUSTRO_ESTUDIANTES:
            self.model.empadronar_alumno(dni, nombre)
        if claustro == api.CLAUSTRO_GRADUADOS:
            self.model.empadronar_graduado(dni, nombre)
        if claustro == api.CLAUSTRO_PROFESORES:
            self.model.empadronar_profesor(dni, nombre)

        # Asegurar que se requiera un ID de agrupación política válido
        with self.assertRaises(IntegrityError):
            self.model.crear_consejero_directivo(dni, periodo, 0)

        self.model.crear_consejero_directivo(dni, periodo, id_agrupacion_politica)

        # Asegurar que no se permita crear el mismo consejero directivo dos veces
        with self.assertRaises(IntegrityError):
            self.model.crear_consejero_directivo(dni, periodo, id_agrupacion_politica)

        # Verificar que se haya creado la entrada en la tabla consejero_directivo
        self.assertSelectEquals('''SELECT id_agrupacion_politica, claustro FROM consejero_directivo
                                   WHERE dni = ? AND periodo = ?''', (dni, periodo),
                                (id_agrupacion_politica, claustro))

    ################################################################################
    # Decano                                                                       #
    ################################################################################

    def test_crear_decano(self):
        dni_inexistente = 0
        dni_estudiante = 123
        dni_graduado = 456
        dni_profesor = 789
        nombre = 'Empadronado'
        periodo = 2014

        self.model.empadronar_alumno(dni_estudiante, nombre)
        self.model.empadronar_graduado(dni_graduado, nombre)
        self.model.empadronar_profesor(dni_profesor, nombre)

        # Asegurar que sea imposible crear un decano con un DNI no empadronado
        with self.assertRaises(IntegrityError):
            self.model.crear_decano(dni_inexistente, periodo)

        # Asegurar que un estudiante no pueda ser decano
        with self.assertRaises(IntegrityError):
            self.model.crear_decano(dni_estudiante, periodo)

        # Asegurar que un graduado no pueda ser decano
        with self.assertRaises(IntegrityError):
            self.model.crear_decano(dni_graduado, periodo)

        self.model.crear_decano(dni_profesor, periodo)

        # Asegurar que no se pueda crear un mismo decano más de una vez
        with self.assertRaises(IntegrityError):
            self.model.crear_decano(dni_profesor, periodo)

        # Verificar que se haya creado la entrada en la tabla decano
        self.assertSelectIsNotEmpty('SELECT * FROM decano WHERE dni = ? AND periodo = ?',
                                    (dni_profesor, periodo))

    def test_registrar_voto_a_decano(self):
        dni_decano = 123
        periodo_decano = 2014
        nombre_decano = 'Decano'
        dni_consejero_directivo = 456
        periodo_consejero_directivo = 2014
        nombre_consejero_directivo = 'Consejero Directivo'
        nombre_agrupacion_politica = u'Agrupación'

        self.model.empadronar_profesor(dni_decano, nombre_decano)
        self.model.empadronar_alumno(dni_consejero_directivo, nombre_consejero_directivo)
        self.model.crear_decano(dni_decano, periodo_decano)
        id_agrupacion_politica = self.model.crear_agrupacion_politica(nombre_agrupacion_politica)
        self.model.crear_consejero_directivo(dni_consejero_directivo, periodo_consejero_directivo, id_agrupacion_politica)

        # Asegurar que sea imposible registrar un voto de un consejero inexistente a un decano inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_decano(0, 0, 0, '')

        # Asegurar que sea imposible registrar un voto de un consejero inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_decano(dni_decano, periodo_decano, 0, 0)

        # Asegurar que sea imposible registrar un voto de a un decano inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_decano(0, 0, dni_consejero_directivo, periodo_consejero_directivo)

        self.model.registrar_voto_a_decano(dni_decano, periodo_decano, dni_consejero_directivo, periodo_consejero_directivo)

        # Asegurar que no se pueda registrar el mismo voto más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_decano(dni_decano, periodo_decano, dni_consejero_directivo, periodo_consejero_directivo)

        # Verificar que se haya creado la entrada en la tabla voto_a_decano
        self.assertSelectIsNotEmpty('''SELECT * FROM voto_a_decano WHERE
                                       dni_decano = ? AND periodo_decano = ? AND
                                       dni_consejero_directivo = ? AND periodo_consejero_directivo = ?''',
                                    (dni_decano, periodo_decano, dni_consejero_directivo, periodo_consejero_directivo))

    ################################################################################
    # Consejo superior                                                             #
    ################################################################################

    def test_crear_consejero_superior_claustro_estudiantes(self):
        self.crear_consejero_superior(api.CLAUSTRO_ESTUDIANTES)

    def test_crear_consejero_superior_claustro_graduados(self):
        self.crear_consejero_superior(api.CLAUSTRO_GRADUADOS)

    def test_crear_consejero_superior_claustro_graduados(self):
        self.crear_consejero_superior(api.CLAUSTRO_PROFESORES)

    def crear_consejero_superior(self, claustro):
        dni = 123
        nombre = 'Consejero'
        periodo = 2014

        # Asegurar que un DNI no empadronado no pueda ser consejero superior
        with self.assertRaises(AssertionError):
            self.model.crear_consejero_superior(dni, periodo)

        # Empadronar el DNI en el padrón correspondiente
        if claustro == api.CLAUSTRO_ESTUDIANTES:
            self.model.empadronar_alumno(dni, nombre)
        if claustro == api.CLAUSTRO_GRADUADOS:
            self.model.empadronar_graduado(dni, nombre)
        if claustro == api.CLAUSTRO_PROFESORES:
            self.model.empadronar_profesor(dni, nombre)

        self.model.crear_consejero_superior(dni, periodo)

        # Asegurar que no se permita crear el mismo consejero superior dos veces
        with self.assertRaises(IntegrityError):
            self.model.crear_consejero_superior(dni, periodo)

        # Verificar que se haya creado la entrada en la tabla consejero_superior
        self.assertSelectEquals('''SELECT claustro FROM consejero_superior
                                   WHERE dni = ? AND periodo = ?''', (dni, periodo), (claustro,))

    def test_registrar_voto_a_consejero_superior(self):
        dni_consejero_superior = 123
        periodo_consejero_superior = 2014
        nombre_consejero_superior = 'Consejero Superior'
        dni_consejero_directivo = 456
        periodo_consejero_directivo = 2014
        nombre_consejero_directivo = 'Consejero Directivo'
        nombre_agrupacion_politica = u'Agrupación'

        self.model.empadronar_alumno(dni_consejero_superior, nombre_consejero_superior)
        self.model.empadronar_alumno(dni_consejero_directivo, nombre_consejero_directivo)
        self.model.crear_consejero_superior(dni_consejero_superior, periodo_consejero_superior)
        id_agrupacion_politica = self.model.crear_agrupacion_politica(nombre_agrupacion_politica)
        self.model.crear_consejero_directivo(dni_consejero_directivo, periodo_consejero_directivo, id_agrupacion_politica)

        # Asegurar que sea imposible registrar un voto de un consejero directivo inexistente a un consejero superior inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_consejero_superior(0, 0, 0, '')

        # Asegurar que sea imposible registrar un voto de un consejero directivo inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_consejero_superior(dni_consejero_superior, periodo_consejero_superior, 0, 0)

        # Asegurar que sea imposible registrar un voto de a un consejero superior inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_consejero_superior(0, 0, dni_consejero_directivo, periodo_consejero_directivo)

        self.model.registrar_voto_a_consejero_superior(dni_consejero_superior, periodo_consejero_superior, dni_consejero_directivo, periodo_consejero_directivo)

        # Asegurar que no se pueda registrar el mismo voto más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_a_consejero_superior(dni_consejero_superior, periodo_consejero_superior, dni_consejero_directivo, periodo_consejero_directivo)

        # Verificar que se haya creado la entrada en la tabla voto_a_consejero_superior
        self.assertSelectIsNotEmpty('''SELECT * FROM voto_a_consejero_superior WHERE
                                       dni_consejero_superior = ? AND periodo_consejero_superior = ? AND
                                       dni_consejero_directivo = ? AND periodo_consejero_directivo = ?''',
                                    (dni_consejero_superior, periodo_consejero_superior, dni_consejero_directivo, periodo_consejero_directivo))

    ################################################################################
    # Rector                                                                       #
    ################################################################################

    def test_crear_rector(self):
        dni_inexistente = 0
        dni_estudiante = 123
        dni_graduado = 456
        dni_profesor = 789
        nombre = 'Empadronado'
        periodo = 2014

        self.model.empadronar_alumno(dni_estudiante, nombre)
        self.model.empadronar_graduado(dni_graduado, nombre)
        self.model.empadronar_profesor(dni_profesor, nombre)

        # Asegurar que sea imposible crear un rector con un DNI no empadronado
        with self.assertRaises(IntegrityError):
            self.model.crear_rector(dni_inexistente, periodo)

        # Asegurar que un estudiante no pueda ser rector
        with self.assertRaises(IntegrityError):
            self.model.crear_rector(dni_estudiante, periodo)

        # Asegurar que un graduado no pueda ser rector
        with self.assertRaises(IntegrityError):
            self.model.crear_rector(dni_graduado, periodo)

        self.model.crear_rector(dni_profesor, periodo)

        # Asegurar que no se pueda crear un mismo rector más de una vez
        with self.assertRaises(IntegrityError):
            self.model.crear_rector(dni_profesor, periodo)

        # Verificar que se haya creado la entrada en la tabla rector
        self.assertSelectIsNotEmpty('SELECT * FROM rector WHERE dni = ? AND periodo = ?',
                                    (dni_profesor, periodo))

    def test_registrar_voto_de_consejero_directivo_a_rector(self):
        dni_rector = 123
        periodo_rector = 2014
        nombre_rector = 'Rector'
        dni_consejero_directivo = 456
        periodo_consejero_directivo = 2014
        nombre_consejero_directivo = 'Consejero Directivo'
        nombre_agrupacion_politica = u'Agrupación'

        self.model.empadronar_profesor(dni_rector, nombre_rector)
        self.model.empadronar_alumno(dni_consejero_directivo, nombre_consejero_directivo)
        self.model.crear_rector(dni_rector, periodo_rector)
        id_agrupacion_politica = self.model.crear_agrupacion_politica(nombre_agrupacion_politica)
        self.model.crear_consejero_directivo(dni_consejero_directivo, periodo_consejero_directivo, id_agrupacion_politica)

        # Asegurar que sea imposible registrar un voto de un consejero inexistente a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_directivo_a_rector(0, 0, 0, '')

        # Asegurar que sea imposible registrar un voto de un consejero inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_directivo_a_rector(dni_rector, periodo_rector, 0, 0)

        # Asegurar que sea imposible registrar un voto de a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_directivo_a_rector(0, 0, dni_consejero_directivo, periodo_consejero_directivo)

        self.model.registrar_voto_de_consejero_directivo_a_rector(dni_rector, periodo_rector, dni_consejero_directivo, periodo_consejero_directivo)

        # Asegurar que no se pueda registrar el mismo voto más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_directivo_a_rector(dni_rector, periodo_rector, dni_consejero_directivo, periodo_consejero_directivo)

        # Verificar que se haya creado la entrada en la tabla voto_a_rector
        self.assertSelectIsNotEmpty('''SELECT * FROM rector_fue_votado_por_consejero_directivo WHERE
                                       dni_rector = ? AND periodo_rector = ? AND
                                       dni_consejero_directivo = ? AND periodo_consejero_directivo = ?''',
                                    (dni_rector, periodo_rector, dni_consejero_directivo, periodo_consejero_directivo))

    def test_registrar_voto_de_consejero_superior_a_rector(self):
        dni_rector = 123
        periodo_rector = 2014
        nombre_rector = 'Rector'
        dni_consejero_superior = 456
        periodo_consejero_superior = 2014
        nombre_consejero_superior = 'Consejero Superior'

        self.model.empadronar_profesor(dni_rector, nombre_rector)
        self.model.empadronar_alumno(dni_consejero_superior, nombre_consejero_superior)
        self.model.crear_rector(dni_rector, periodo_rector)
        self.model.crear_consejero_superior(dni_consejero_superior, periodo_consejero_superior)

        # Asegurar que sea imposible registrar un voto de un consejero inexistente a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_superior_a_rector(0, 0, 0, '')

        # Asegurar que sea imposible registrar un voto de un consejero inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_superior_a_rector(dni_rector, periodo_rector, 0, 0)

        # Asegurar que sea imposible registrar un voto de a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_superior_a_rector(0, 0, dni_consejero_superior, periodo_consejero_superior)

        self.model.registrar_voto_de_consejero_superior_a_rector(dni_rector, periodo_rector, dni_consejero_superior, periodo_consejero_superior)

        # Asegurar que no se pueda registrar el mismo voto más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_consejero_superior_a_rector(dni_rector, periodo_rector, dni_consejero_superior, periodo_consejero_superior)

        # Verificar que se haya creado la entrada en la tabla voto_a_rector
        self.assertSelectIsNotEmpty('''SELECT * FROM rector_fue_votado_por_consejero_superior WHERE
                                       dni_rector = ? AND periodo_rector = ? AND
                                       dni_consejero_superior = ? AND periodo_consejero_superior = ?''',
                                    (dni_rector, periodo_rector, dni_consejero_superior, periodo_consejero_superior))

    def test_registrar_voto_de_decano_a_rector(self):
        dni_rector = 123
        periodo_rector = 2014
        nombre_rector = 'Rector'
        dni_decano = 456
        periodo_decano = 2014
        nombre_decano = 'Decano'

        self.model.empadronar_profesor(dni_rector, nombre_rector)
        self.model.empadronar_profesor(dni_decano, nombre_decano)
        self.model.crear_rector(dni_rector, periodo_rector)
        self.model.crear_decano(dni_decano, periodo_decano)

        # Asegurar que sea imposible registrar un voto de un decano inexistente a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_decano_a_rector(0, 0, 0, '')

        # Asegurar que sea imposible registrar un voto de un decano inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_decano_a_rector(dni_rector, periodo_rector, 0, 0)

        # Asegurar que sea imposible registrar un voto de a un rector inexistente
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_decano_a_rector(0, 0, dni_decano, periodo_decano)

        self.model.registrar_voto_de_decano_a_rector(dni_rector, periodo_rector, dni_decano, periodo_decano)

        # Asegurar que no se pueda registrar el mismo voto más de una vez
        with self.assertRaises(IntegrityError):
            self.model.registrar_voto_de_decano_a_rector(dni_rector, periodo_rector, dni_decano, periodo_decano)

        # Verificar que se haya creado la entrada en la tabla voto_a_rector
        self.assertSelectIsNotEmpty('''SELECT * FROM rector_fue_votado_por_decano WHERE
                                       dni_rector = ? AND periodo_rector = ? AND
                                       dni_decano = ? AND periodo_decano = ?''',
                                    (dni_rector, periodo_rector, dni_decano, periodo_decano))

    ################################################################################
    # Aserciones auxiliares                                                        #
    ################################################################################

    # Ejecuta la consulta y verifica que el conjunto de filas devuelto sea no-vacío
    def assertSelectIsNotEmpty(self, query, parameters):
        with self.connector as c:
            c.execute(query, parameters)
            row = c.fetchone()
            self.assertIsNotNone(row)

    # Ejecuta la consulta y verifica que la primera fila devuelta coincida con la fila recibida por parámetro
    def assertSelectEquals(self, query, parameters, expected_row):
        with self.connector as c:
            c.execute(query, parameters)
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEquals(row, expected_row)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModel)
    unittest.TextTestRunner(verbosity=2).run(suite)
