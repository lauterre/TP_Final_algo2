from copy import deepcopy
from typing import Any
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from metricas import Metricas
from _superclases import ArbolClasificador
from graficador import GraficadorArbol

class ArbolClasificadorID3(ArbolClasificador):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
    def _mejor_atributo_split(self) -> str | None:
        mejor_ig = -1
        mejor_atributo = None
        atributos = self.data.columns

        for atributo in atributos:
            if len(self.data[atributo].unique()) > 1:
                ig = self._information_gain(atributo)
                if ig > mejor_ig:
                    mejor_ig = ig
                    mejor_atributo = atributo

        return mejor_atributo
    
    def copy(self):
        nuevo = ArbolClasificadorID3(**self.__dict__)
        nuevo.data = self.data.copy()
        nuevo.target = self.target.copy()
        nuevo.target_categorias = self.target_categorias.copy()
        nuevo.subs = [sub.copy() for sub in self.subs]
        return nuevo
        
    def _split(self, atributo: str) -> None:
        
        temp = deepcopy(self)  # TODO: arreglar copy
        self.atributo_split = atributo  # guardo el atributo por el cual spliteo

        for categoria in self.data[atributo].unique():  # recorre el dominio de valores del atributo
            nueva_data = self.data[self.data[atributo] == categoria]
            nueva_data = nueva_data.drop(atributo, axis=1)  # la data del nuevo nodo sin el atributo por el cual ya se filtró
            nuevo_target = self.target[self.data[atributo] == categoria]

            nuevo_arbol = ArbolClasificadorID3()  # Crea un nuevo arbol
            nuevo_arbol.data = nueva_data  # Asigna nodo
            nuevo_arbol.target = nuevo_target  # Asigna target
            nuevo_arbol.valor_split_anterior = categoria
            nuevo_arbol.atributo_split_anterior = atributo
            nuevo_arbol.set_clase()
            temp.agregar_subarbol(nuevo_arbol)  # Agrego el nuevo arbol en el arbol temporal

        ok_min_obs_hoja = True
        for sub_arbol in temp.subs:
            if (self.min_obs_hoja !=-1 and sub_arbol._total_samples() < self.min_obs_hoja):
                ok_min_obs_hoja = False

        if ok_min_obs_hoja:
            self.subs = temp.subs
    
    def _information_gain(self, atributo: str) -> float:
        entropia_actual = self._entropia()
        len_actual = self._total_samples()

        nuevo = self.copy()

        nuevo._split(atributo)

        entropias_subarboles = 0 
        for subarbol in nuevo.subs:
            entropia = subarbol._entropia()
            len_subarbol = subarbol._total_samples()
            entropias_subarboles += ((len_subarbol/len_actual) * entropia)

        information_gain = entropia_actual - entropias_subarboles
        return information_gain
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.target = y
        self.data = X
        self.set_clase()

        def _interna(arbol: ArbolClasificadorID3, prof_acum: int = 1):
            arbol.set_target_categorias(y)

            if arbol._puede_splitearse(prof_acum):
                mejor_atributo = arbol._mejor_atributo_split()

                if mejor_atributo:
                    mejor_ig = arbol._information_gain(mejor_atributo)

                    if (arbol.min_infor_gain == -1 or mejor_ig >= arbol.min_infor_gain):
                        arbol._split(mejor_atributo)

                        for sub_arbol in arbol.subs:
                            _interna(sub_arbol, prof_acum + 1)
                    
        _interna(self)
        
    def predict(self, X: pd.DataFrame) -> list[str]:
        predicciones = []
        def _recorrer(arbol, fila: pd.Series) -> None:
            if arbol.es_hoja():
                predicciones.append(arbol.clase)
            else:
                direccion = fila[arbol.atributo_split]
                existe = False
                for subarbol in arbol.subs:
                    if direccion == subarbol.valor_split_anterior:
                        existe = True
                        _recorrer(subarbol, fila)
                if not existe:
                    predicciones.append(predicciones[0])

        for _, fila in X.iterrows():
            _recorrer(self, fila)

        return predicciones

    def imprimir(self, prefijo: str = '  ', es_ultimo: bool = True) -> None:
        simbolo_rama = '└─── ' if es_ultimo else '├─── '
        split = "Split: " + str(self.atributo_split)
        rta =  f"{self.atributo_split_anterior} = {self.valor_split_anterior}"
        entropia = f"Entropia: {round(self._entropia(), 2)}"
        samples = f"Samples: {str(self._total_samples())}"
        values = f"Values: {str(self._values())}"
        clase = 'Clase: ' + str(self.clase)
        
        if self.es_raiz():
            print(entropia)
            print(samples)
            print(values)
            print(clase)
            print(split)

            for i, sub_arbol in enumerate(self.subs):
                ultimo: bool = i == len(self.subs) - 1
                sub_arbol.imprimir(prefijo, ultimo)

        elif not self.es_hoja():
            print(prefijo + "│")
            print(prefijo + simbolo_rama + rta)
            prefijo2 = prefijo + " " * (len(simbolo_rama)) if es_ultimo else prefijo +"│" + " " * (len(simbolo_rama) - 1)
            print(prefijo2 + entropia)
            print(prefijo2 + samples)
            print(prefijo2 + values)
            print(prefijo2 + clase)
            print(prefijo2 + split)

            prefijo += ' ' * 10 if es_ultimo else '│' + ' ' * 9
            for i, sub_arbol in enumerate(self.subs):
                ultimo: bool = i == len(self.subs) - 1
                sub_arbol.imprimir(prefijo, ultimo)
        else:
            prefijo_hoja = prefijo + " " * len(simbolo_rama) if es_ultimo else prefijo + "│" + " " * (len(simbolo_rama) - 1)
            print(prefijo + "│")
            print(prefijo + simbolo_rama + rta)
            print(prefijo_hoja + entropia)
            print(prefijo_hoja + samples)
            print(prefijo_hoja + values)
            print(prefijo_hoja + clase)
        
    def graficar(self):
        plotter = GraficadorArbol(self)
        plotter.plot()
        
    def _error_clasificacion(self, y, y_pred):
        x = []
        for i in range(len(y)):
            x.append(y[i] != y_pred[i])
        return np.mean(x)
        
    def Reduced_Error_Pruning(self, x_test: Any, y_test: Any):
        def _interna_REP(arbol: ArbolClasificadorID3, x_test, y_test):
            if arbol.es_hoja():
                return

            for subarbol in arbol.subs:
                _interna_REP(subarbol, x_test, y_test)

                pred_raiz: list[str] = arbol.predict(x_test)
                accuracy_raiz = Metricas.accuracy_score(y_test.tolist(), pred_raiz)
                error_clasif_raiz = arbol._error_clasificacion(y_test.tolist(), pred_raiz)

                error_clasif_ramas = 0.0

                for rama in arbol.subs:
                    new_arbol: ArbolClasificadorID3 = rama
                    pred_podada = new_arbol.predict(x_test)
                    accuracy_podada = Metricas.accuracy_score(y_test.tolist(), pred_podada)
                    error_clasif_podada = new_arbol._error_clasificacion(y_test.tolist(), pred_podada)
                    error_clasif_ramas = error_clasif_ramas + error_clasif_podada

                if error_clasif_ramas < error_clasif_raiz:
                    #print(" * Podar \n")
                    arbol.subs = []
                #else:
                    #print(" * No podar \n")

        _interna_REP(self, x_test, y_test)

def probar(df, target: str):
    X = df.drop(target, axis=1)
    y = df[target]

    x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    #arbol = ArbolClasificadorID3(min_obs_nodo=1)
    #arbol = ArbolClasificadorID3(min_infor_gain=0.85)
    arbol = ArbolClasificadorID3()
    arbol.fit(x_train, y_train)
    arbol.imprimir()
    arbol.graficar()
    y_pred = arbol.predict(x_test)

    #arbol.Reduced_Error_Pruning(x_test, y_test)

    print(f"\n accuracy: {Metricas.accuracy_score(y_test, y_pred):.2f}")
    print(f"f1-score: {Metricas.f1_score(y_test, y_pred, promedio='ponderado')}\n")

if __name__ == "__main__":
    patients = pd.read_csv("./datasets/cancer_patients.csv", index_col=0)
    patients = patients.drop("Patient Id", axis = 1)
    bins = [0, 15, 20, 30, 40, 50, 60, 70, float('inf')]
    labels = ['0-15', '15-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70+']
    patients['Age'] = pd.cut(patients['Age'], bins=bins, labels=labels, right=False)

    tennis = pd.read_csv("./datasets/PlayTennis.csv")

    print("Pruebo con patients")
    probar(patients, "Level")
    print("Pruebo con Play Tennis")
    probar(tennis, "Play Tennis")
