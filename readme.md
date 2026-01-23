tamagotchi-hedonista

Quiero hacer una especie de "tamagotchi" o sims pero especializado en simulacion de humanos, en particular para buscar combinaciones de eventos y estimulos que generen sesiones de algunas horas de mucho placer. Por ejemplo tener sexo yendo lento y postergando o evitando el orgasmo es un clasico, pero despues pueden haber cosas mas inesperadas, como sumarle a eso un poco de adrenalina con algo que de culpa o con un poco de dolor. Por eso me gustaria hacer un programa que tenga esta simulacion basica de ser humano sin interfaz grafica ni nada pero que tenga valores fisiologicos basicos como niveles de distintos neurotransmisores, HR y demas, y que tenga esta gran lista de eventos y de como afectan a la fisiologia los mismos y como interactuan, deje al final del documento una idea inicial.

Quiero arrancar con un MVP muy basico e ir haciendolo crecer, puede ser muy acotado al principio. Me gustaria empezar con algo con pocos eventos e intentar ver si programandolo para que maximice algo, por ejemplo niveles de dopamina+endorfinas+oxitocina altos por la mayor cantidad de horas encuentre combinaciones interesantes de estimulos para lograrlo.

--------------------


Refes:
- tamagotchi
- sims y simcity
- dwarf fortress
- sandspiel.club y orb.farm (Max Bittker and Lu Wilson projeects)
    - https://studio.sandspiel.club/
    - https://sandpond.cool/
- boids

Some ideas
- estimulacion sexual produce arousal y placer pero puede producir orgasmos con eyaculacion lo cual baja de forma brusca la dopamina
- arousal alto produce energia y hambre a lo largo del tiempo
- interacciones sociales pueden producir oxitocina y vasopresina pero tambien ansiedad, monologo interno alto y atencion dirigida a cosas por fuera del placer o el trance
- serotonina produce bienestar, confianza pero tambien prolactina y disminucion de picos de dopamina
- pequeñas dosis de miedo, asco, culpa producen adrenalina, dopamina o cosas asi que se pueden usarpara potenciar placer
- pero si te pasas pueden llevar la atencion a otro lado, activar el cortex prefrontal, sacar la atencion del placer

-----------------

humano
- nivel de cada neurotransmisor
- nivel de arousal (latidos, presion, pupilas, )
- nivel de activacion de cortex prefrontal
- atencion dirigida a / saliencia

## eventos internos del juego y funciones auxiliares

def paso_del_tiempo(h)
    h.hambre = h.hambre+1
    h.energia=h.energia-1

### respuestas fisiologicas comunes (funcion util ya que esto lo disparan muchas acciones)

def flight_or_fight(self, intensity):
    self.hambre = 0
    self.hr *= 1+intensity/20
    self.hr = min(self.hr, 180)

## acciones posibles del jugador

- despertarse despues de dormir bien
    - lambda h : h.energia = 30, h.hambre = 5
- experimentar ice reflex por enfriado de cara
    - lambda h : h.adrenalina = alta, h.palpitaciones = altas, flight_or_fight(h)
- dormirse livianamente
    - lambda h : h.activida_cortex_prefrontal = baja, h.energia=h.energia+3
- tomar popper
    - lambda h : h.activida_cortex_prefrontal = baja, h.saliencia = interna/sensorial, h.presion = alta, ...
