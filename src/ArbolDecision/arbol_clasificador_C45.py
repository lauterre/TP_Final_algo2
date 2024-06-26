import pandas as pd
import numpy as np
import random
from typing import Any, Optional

from src.Impureza.impureza import Entropia
from src.Superclases.superclases import ArbolClasificador, Hiperparametros
from src.Excepciones.excepciones import ArbolNoEntrenadoException, LongitudInvalidaException

'''Documentación para el módulo arbol_clasificador_c45.py'''

class ArbolClasificadorC45(ArbolClasificador):
    '''Clase que implementa un árbol de decisión para clasificación utilizando el algoritmo C4.5'''
    def __init__(self, **kwargs) -> None:
        '''Constructor de la clase ArbolClasificadorC45.
        
        Args:
            **kwargs: hiperparametros del arbol.
            
        Atributos:
            umbral_split(float | str | None): umbral de split para atributos numéricos y ordinales.
            impureza (Entropia): instancia de la clase Entropia que calcula la impureza de un conjunto de datos.
        '''
        super().__init__(**kwargs)
        self.umbral_split: Optional[float | str] = None
        self.impureza = Entropia()
    
    def copy(self) -> "ArbolClasificadorC45":
        '''Devuelve una copia profunda del arbol
        
        Returns:
            ArbolClasificadorC45: copia del arbol'''
        hiperparametros_copiados = {k: v for k, v in self.__dict__.items() if k in Hiperparametros.PARAMS_PERMITIDOS}
        nuevo = ArbolClasificadorC45(**hiperparametros_copiados)
        nuevo.data = self.data.copy()
        nuevo.target = self.target.copy()
        nuevo.target_categorias = self.target_categorias.copy()
        nuevo.set_clase()
        nuevo.atributo_split = self.atributo_split
        nuevo.atributo_split_anterior = self.atributo_split_anterior
        nuevo.valor_split_anterior = self.valor_split_anterior
        nuevo.signo_split_anterior = self.signo_split_anterior
        nuevo.impureza = self.impureza
        nuevo.umbral_split = self.umbral_split 
        nuevo.subs = [sub.copy() for sub in self.subs]
        return nuevo
        
    def _nuevo_subarbol(self, atributo: str, operacion: str, valor: Any) -> None:
        '''Crea un nuevo subarbol y lo agrega a la lista de subarboles del arbol actual.
        
        Args:
            atributo (str): atributo por el cual se va a hacer el split.
            operacion (str): operacion que se va a realizar en el split.
            valor (Any): valor que se va a comparar en el split.
        '''
        hiperparametros_copiados = {k: v for k, v in self.__dict__.items() if k in Hiperparametros.PARAMS_PERMITIDOS}
        nuevo = ArbolClasificadorC45(**hiperparametros_copiados)
        if operacion == "menor":
            nuevo.data = self.data[self.data[atributo] < valor]
            nuevo.target = self.target[self.data[atributo] < valor]
            nuevo.signo_split_anterior = "<"
        
        elif operacion == "mayor":
            nuevo.data = self.data[self.data[atributo] >= valor]
            nuevo.target = self.target[self.data[atributo] >= valor]
            nuevo.signo_split_anterior = ">="
        
        elif operacion == "igual":
            nueva_data = self.data[self.data[atributo] == valor]
            nueva_data = nueva_data.drop(atributo, axis=1)
            nuevo.data = nueva_data
            nuevo.target = self.target[self.data[atributo] == valor]
            nuevo.signo_split_anterior = "="
        
        nuevo.set_clase()
        nuevo.atributo_split_anterior = atributo
        nuevo.valor_split_anterior = valor
        self.agregar_subarbol(nuevo)

    def _split_numerico(self, atributo: str, umbral: float | int) -> None:
        '''Realiza el split en el caso que el atributo sea numérico.
        
        Args:
            atributo (str): atributo por el cual se va a hacer el split.
            umbral (float | int): umbral de split.
        '''
        self.atributo_split = atributo
        self.umbral_split = umbral
        self._nuevo_subarbol(atributo, "menor", umbral)
        self._nuevo_subarbol(atributo, "mayor", umbral)

    def _split_categorico(self, atributo: str) -> None:
        '''Realiza el split en el caso que el atributo sea categórico.
        
        Args:
            atributo (str): atributo por el cual se va a hacer el split.
        '''
        self.atributo_split = atributo
        for categoria in self.data[atributo].unique():
            self._nuevo_subarbol(atributo, "igual", categoria)
    
    def _split_ordinal(self, atributo: str, umbral: str) -> None:
        '''Realiza el split en el caso que el atributo sea ordinal.
        
        Args:
            atributo (str): atributo por el cual se va a hacer el split.
            umbral (str): umbral de split.
        '''
        self.atributo_split = atributo
        self.umbral_split = umbral
        self._nuevo_subarbol(atributo, "menor", umbral)
        self._nuevo_subarbol(atributo, "mayor", umbral)
    
    def _split(self, atributo: str):
        '''Realiza el split en el caso que el atributo sea numérico, ordinal o categórico.'''
        if self.es_atributo_numerico(atributo):
            mejor_umbral = self._mejor_umbral_split_num(atributo)
            self._split_numerico(atributo, mejor_umbral)

        elif self.es_atributo_ordinal(atributo):
            mejor_umbral = self._mejor_umbral_split_ord(atributo)
            self._split_ordinal(atributo, mejor_umbral)

        else:
            self._split_categorico(atributo)

    def es_atributo_numerico(self, atributo: str) -> bool:
        '''Funcion que verifica si un atributo es numerico.
        
        Args:
            atributo (str): nombre del atributo a verificar.
            
        Returns:
            bool: True si el atributo es numerico, False en caso contrario.
        '''
        return pd.api.types.is_numeric_dtype(self.data[atributo])
    
    def es_atributo_ordinal(self, atributo: str) -> bool:
        '''Funcion que verifica si un atributo es ordinal.
        
        Args:
            atributo (str): nombre del atributo a verificar.
            
        Returns:
            bool: True si el atributo es ordinal, False en caso contrario.
        '''
        return isinstance(self.data[atributo].dtype, pd.CategoricalDtype) and self.data[atributo].cat.ordered
    
    def _information_gain(self, atributo: str) -> float:  #calcula el mejor umbral de ser necesario
        '''Calcula la ganancia de información de un atributo.

        Args:
            atributo (str): nombre del atributo a calcular la ganancia de información.

        Returns:
            float: ganancia de información del atributo.
        '''
        def split(arbol, atributo):
            arbol._split(atributo)
        
        return self.impureza.calcular_impureza_split(self, atributo, split)
    
    def _split_info(self):
        '''Calcula el split info del arbol. Mide la dispersión de los valores de los atributos.'''
        split_info = 0
        len_actual = self._total_samples()
        for subarbol in self.subs:
            len_subarbol = subarbol._total_samples()
            split_info += (len_subarbol / len_actual) * np.log2(len_subarbol / len_actual)
        return -split_info
        
    def _gain_ratio(self, atributo: str) -> float:
        '''Calcula el gain ratio de un atributo. El gain ratio es la division de la ganancia de información de un atributo por el split info del mismo atributo.

        Args:
            atributo (str): nombre del atributo a calcular el gain ratio.

        Returns:
            float: gain ratio del atributo.
        '''
        nuevo = self.copy()

        information_gain = nuevo._information_gain(atributo)
        nuevo._split(atributo)
        split_info = nuevo._split_info()

        return information_gain / split_info
    
    def _mejor_atributo_split(self) -> str | None:
        '''Calcula el mejor atributo para hacer el split. El mejor atributo es aquel que maximiza el gain ratio.
        
        Returns:
            str: nombre del mejor atributo para hacer el split.'''
        mejor_gain_ratio = -1
        mejor_atributo = None
        atributos = self.data.columns

        for atributo in atributos:
            if len(self.data[atributo].unique()) > 1:
                gain_ratio = self._gain_ratio(atributo)
                if gain_ratio > mejor_gain_ratio:
                    mejor_gain_ratio = gain_ratio
                    mejor_atributo = atributo

        return mejor_atributo
    
    def __information_gain_numerico(self, atributo: str, umbral: float | int):  # helper de mejor_umbral_split, no calcula el mejor umbral
            def split_num(arbol, atributo):
                arbol._split_numerico(atributo, umbral)
            
            return self.impureza.calcular_impureza_split(self, atributo, split_num)
    
    def __information_gain_ordinal(self, atributo: str, umbral: str):  # helper de mejor_umbral_split, no calcula el mejor umbral
            def split_ord(arbol, atributo):
                arbol._split_ordinal(atributo, umbral)

            return self.impureza.calcular_impureza_split(self, atributo, split_ord)
    
    def _mejor_umbral_split_num(self, atributo: str) -> float:
        '''Calcula el mejor umbral para hacer el split en un atributo numérico.
        
        Args:
            atributo (str): nombre del atributo a calcular el mejor umbral.
            
        Returns:
            float: mejor umbral para hacer el split.
        '''
        self.data = self.data.sort_values(by=atributo)
        self.target = self.target.loc[self.data.index]

        valores_unicos = self.data[atributo].unique()
        target_valores_unicos = []
        for valor in valores_unicos:
            target_valores_unicos.append(self.target[self.data[atributo] == valor].iloc[0])

        mejor_umbral = valores_unicos[0]
        mejor_ig = -1
        i = 0
        while i < len(valores_unicos) - 1:
            if i == 0 or target_valores_unicos[i] != target_valores_unicos[i + 1]:
                umbral = (valores_unicos[i] + valores_unicos[i + 1]) / 2
                ig = self.__information_gain_numerico(atributo, umbral)
                if ig > mejor_ig:
                    mejor_ig = ig
                    mejor_umbral = umbral
            i += 1

        return mejor_umbral 
            
    def _mejor_umbral_split_ord(self, atributo: str) -> str:
        '''Calcula el mejor umbral para hacer el split en un atributo ordinal.

        Args:
            atributo (str): nombre del atributo a calcular el mejor umbral.

        Returns:
            str: mejor umbral para hacer el split.
        '''
        self.data = self.data.sort_values(by=atributo, ascending=False) # porque cuando hacemos el split pedimos que sea < al umbral, si estan de menor a mayor, el primer valor nunca es < al umbral
        mejor_ig = -1
        valores_unicos = self.data[atributo].unique()
        mejor_umbral = valores_unicos[0]

        i = 0
        while i < len(valores_unicos) - 1:
            ig = self.__information_gain_ordinal(atributo, valores_unicos[i])
            if ig > mejor_ig:
                mejor_ig = ig
                mejor_umbral = valores_unicos[i]
            i += 1
        
        return mejor_umbral
    
    def _rellenar_missing_values(self) -> None:
        '''Rellena los valores faltantes de las columnas numéricas con la media y de las columnas categóricas con la moda.'''
        for columna in self.data.columns:
            if self.es_atributo_numerico(columna):
                medias = self.data.groupby(self.target)[columna].transform('mean')
                self.data.fillna({columna: medias}, inplace=True)
            else:
                modas = self.data.groupby(self.target)[columna].transform(lambda x: x.mode()[0] if not x.mode().empty else x)
                self.data.fillna({columna: modas}, inplace=True)
    
    def _puede_splitearse(self, prof_acum: int, mejor_atributo: str) -> bool:  
        '''Verifica si el arbol puede splitearse en base a los hiperparametros y a la ganancia de información del mejor atributo.

        Args:
            prof_acum (int): profundidad acumulada del arbol.
            mejor_atributo (str): mejor atributo para hacer el split.

        Returns:
            bool: True si el arbol puede splitearse, False en caso contrario.
        '''
        copia = self.copy()
        information_gain = self._information_gain(mejor_atributo)
        copia._split(mejor_atributo)
        for subarbol in copia.subs:
            if self.min_obs_hoja != -1 and subarbol._total_samples() < self.min_obs_hoja:
                return False
            
        return not (len(self.target.unique()) == 1 or len(self.data.columns) == 0
                    or (self.max_prof != -1 and self.max_prof <= prof_acum)
                    or (self.min_obs_nodo != -1 and self.min_obs_nodo > self._total_samples())
                    or (self.min_infor_gain != -1 and self.min_infor_gain > information_gain))

    def fit(self, X: pd.DataFrame, y: pd.Series):
        '''Entrena el arbol de decisión con los datos de entrada.

        Args:
            X (pd.DataFrame): datos de entrenamiento.
            y (pd.Series): vector con el atributo a predecir.
        '''
        if len(X) != len(y):
            raise LongitudInvalidaException(f"Error: Longitud de X e y no coinciden")
        self.target = y.copy()
        self.data = X.copy()
        self._rellenar_missing_values()
        self.set_clase()
        
        def _interna(arbol, prof_acum: int = 1):
            arbol.set_target_categorias(y)

            mejor_atributo = arbol._mejor_atributo_split()
            if mejor_atributo and arbol._puede_splitearse(prof_acum, mejor_atributo):
                arbol._split(mejor_atributo)
                
                for sub_arbol in arbol.subs:
                    _interna(sub_arbol, prof_acum + 1)
        
        _interna(self)   
        
    def predict(self, X: pd.DataFrame) -> list:
        '''Predice la clase de las instancias de entrada. 
        En caso de que haya valores faltantes en las instancias, se predice con la probabilidad de las clases de los subarboles.

        Args:
            X (pd.DataFrame): instancias a predecir.

        Returns:
            predicciones (list): lista con las predicciones.
        '''
        predicciones = []
        if self.data is None or self.target is None:
            raise ArbolNoEntrenadoException()
        
        def _recorrer(arbol, fila: pd.Series):
            if arbol.es_hoja():
                return arbol.clase
            else:
                valor = fila[arbol.atributo_split]
                if pd.isna(valor):  # Manejar valores faltantes en la predicción
                    dist_probabilidades = _predict_valor_faltante(arbol, fila)
                    return _obtener_clase_aleatoria(dist_probabilidades)          
                if arbol.es_atributo_numerico(arbol.atributo_split):
                    if valor < arbol.umbral_split:
                        return _recorrer(arbol.subs[0], fila)
                    else:
                        return _recorrer(arbol.subs[1], fila)
                elif arbol.es_atributo_ordinal(arbol.atributo_split):
                    niveles_ordenados = arbol.data[arbol.atributo_split].cat.categories
                    posicion_valor = niveles_ordenados.get_loc(valor)
                    posicion_umbral = niveles_ordenados.get_loc(arbol.umbral_split)
                    if posicion_valor < posicion_umbral:
                        return _recorrer(arbol.subs[0], fila)
                    else:
                        return _recorrer(arbol.subs[1], fila)
                else:
                    for subarbol in arbol.subs:
                        if valor == subarbol.valor_split_anterior:
                            return _recorrer(subarbol, fila)

        def _predict_valor_faltante(arbol, fila):
            total_samples = arbol._total_samples()
            probabilidades = {clase: 0 for clase in arbol.target_categorias}
            for subarbol in arbol.subs:
                sub_samples = subarbol._total_samples()
                sub_prob = sub_samples / total_samples
                if subarbol.es_hoja():
                    for i, clase in enumerate(arbol.target_categorias):
                        probabilidades[clase] += subarbol._values()[i] 
                else:
                    sub_probs = _predict_valor_faltante(subarbol, fila) 
                    for i, clase in enumerate(arbol.target_categorias):
                        probabilidades[clase] += sub_probs[clase] 
            return probabilidades
        
        def _obtener_clase_aleatoria(diccionario_probabilidades):
                cantidad_total = sum(diccionario_probabilidades.values())
                for key in diccionario_probabilidades:
                    diccionario_probabilidades[key] = round(diccionario_probabilidades[key] / cantidad_total,2) #Redondeado para que se entienda mas
                total_valores = sum(diccionario_probabilidades.values())
                probabilidades = [valor / total_valores for valor in diccionario_probabilidades.values()]
                clases = list(diccionario_probabilidades.keys())
                
                clase_aleatoria = random.choices(clases, weights=probabilidades, k=1)[0]
                print(diccionario_probabilidades,clase_aleatoria)
                return clase_aleatoria

        for _, fila in X.iterrows():
            prediccion = _recorrer(self, fila)
            #print(prediccion)
            predicciones.append(prediccion)

        return predicciones

    def __str__(self) -> str:
        if self.data is None or self.target is None:
            raise ArbolNoEntrenadoException()
        out = []
        def _interna(arbol, prefijo: str = '  ', es_ultimo: bool = True) -> None:
            if arbol.signo_split_anterior != "=":
                simbolo_rama = '└─ NO ── ' if es_ultimo else '├─ SI ── '
            else:
                simbolo_rama = '└─── ' if es_ultimo else '├─── '
            
            if arbol.atributo_split and arbol.es_atributo_numerico(arbol.atributo_split):
                split = f"{arbol.atributo_split} < {round(arbol.umbral_split, 2)} ?" if arbol.umbral_split else ""
            elif arbol.atributo_split and arbol.es_atributo_ordinal(arbol.atributo_split):
                split = f"{arbol.atributo_split} < {arbol.umbral_split} ?" if arbol.umbral_split else ""
            else:
                split = str(arbol.atributo_split) + " ?"

            
            impureza = f"{arbol.impureza}: {round(arbol.impureza.calcular(arbol.target), 3)}"
            samples = f"Muestras: {arbol._total_samples()}"
            values = f"Conteo: {arbol._values()}"
            clase = f"Clase: {arbol.clase}"

            if arbol.es_raiz():
                out.append(impureza)
                out.append(samples)
                out.append(values)
                out.append(clase)
                out.append(split)

                for i, sub_arbol in enumerate(arbol.subs):
                    ultimo: bool = i == len(arbol.subs) - 1
                    _interna(sub_arbol, prefijo, ultimo)

            elif arbol.es_hoja():
                prefijo_hoja = prefijo + " " * len(simbolo_rama) if es_ultimo else prefijo + "│" + " " * (len(simbolo_rama) - 1)
                out.append(prefijo + "│")
                            
                if arbol.signo_split_anterior != "=":
                    out.append(prefijo + simbolo_rama + impureza)
                    out.append(prefijo_hoja + samples)
                    out.append(prefijo_hoja + values)
                    out.append(prefijo_hoja + clase)
                else:
                    rta =  f"{arbol.atributo_split_anterior} = {arbol.valor_split_anterior}"
                    out.append(prefijo + simbolo_rama + rta)            
                    out.append(prefijo_hoja + impureza)
                    out.append(prefijo_hoja + samples)
                    out.append(prefijo_hoja + values)
                    out.append(prefijo_hoja + clase)
            
            else:
                out.append(prefijo + "│")
                
                #if arbol.atributo_split and (arbol.es_atributo_numerico(arbol.atributo_split) or arbol.es_atributo_ordinal(arbol.atributo_split)):
                if arbol.signo_split_anterior != "=":
                    out.append(prefijo + simbolo_rama + impureza)
                    prefijo2 = prefijo + " " * (len(simbolo_rama)) if es_ultimo else prefijo + "│" + " " * (len(simbolo_rama) - 1)
                    out.append(prefijo2 + samples)
                    out.append(prefijo2 + values)
                    out.append(prefijo2 + clase)
                    out.append(prefijo2 + split)
                else:
                    rta =  f"{arbol.atributo_split_anterior} = {arbol.valor_split_anterior}"
                    out.append(prefijo + simbolo_rama + rta)            
                    prefijo2 = prefijo + " " * (len(simbolo_rama)) if es_ultimo else prefijo + "│" + " " * (len(simbolo_rama) - 1)
                    out.append(prefijo2 + impureza)
                    out.append(prefijo2 + samples)
                    out.append(prefijo2 + values)
                    out.append(prefijo2 + clase)
                    out.append(prefijo2 + split)

                prefijo += ' ' * 10 if es_ultimo else '│' + ' ' * 9
                for i, sub_arbol in enumerate(arbol.subs):
                    ultimo: bool = i == len(arbol.subs) - 1
                    _interna(sub_arbol, prefijo, ultimo)
        _interna(self)
        return "\n".join(out)