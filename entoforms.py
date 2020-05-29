import bpy
import random

########################
# Variables global
########################

pm = 0.25  # probabilitée de mutation
pc = 0.85  # probabilitée de crossover
e  = 0.10  # pourcentage d'élite que l'on conserve
d  = 2     # nombre de plus mauvais que l'on détruit
m  = 2     # nombre de paramètre


########################
# Fonctions
########################

# Custom mode_set
def mode_set(mode='OBJECT'):
    # Si le mode voulu et déjà celui actuel cela va généré une erreur
    # On choisi de l'ignorer
    try:
        bpy.ops.object.mode_set(mode=mode)
    except RuntimeError:
        pass

# Nettoye la scene en supprimant tout les mesh
def clear_scene():
    mode_set(mode = 'OBJECT')
        
    bpy.ops.object.select_by_type(type="MESH")
    bpy.ops.object.delete()

# Convertie un tableau de bit, en un entier en base 10
def bitshifting(bitlist):
    out = 0
    for bit in bitlist:
        out = (out << 1) | bit
    return out

# Convertie un entier en un tableau de bit
def to_bitlist(number):
    out = []
    bites = "{0:b}".format(number)
    for i in range(8 - len(bites)):
        out.append(0)
    for bit in bites:
        out.append(int(bit))
    return out

# https://en.wikipedia.org/wiki/Fitness_proportionate_selection
def roulette_wheel_selection(choices):
    max = sum([choice['fitness'] for choice in choices])
    if max == 0:
        return random.choice([c['index'] for c in choices])
    pick = random.uniform(0, max)
    current = 0
    for choice in choices:
        current += choice['fitness']
        if current > pick:
            return choice['index']

########################
# Classes
########################

class GenState(object):
    population = []
    generation = 0  # numéro de la génération
    
    def __init__(self):
        self.population = [Entoform() for i in range(9)]
        self.generation_count = 0
        
    def evolve(self, selected_objects_index=[]):
        self.generation += 1
        
        # Interactive Selection
        # selected_objects_index = [int(obj.name.replace("Cube","")) for obj in bpy.context.selected_objects]
        
        # Construction du tableau de fitness
        population_fitness = [{'fitness': 1 if i in selected_objects_index else 0, 'index': i} for i in range(len(self.population))]
        # On normalise les valeur (entre 0 et 1)
        sum_fitness = sum(pop_fit['fitness'] for pop_fit in population_fitness)
        if not sum_fitness == 0:
            for i in range(len(population_fitness)):
                population_fitness[i]['fitness'] = float(population_fitness[i]['fitness']) / sum_fitness
        # Et on le tri
        population_fitness = sorted(population_fitness, key=lambda x : x['fitness'])
        
        if random.random() < pm:
            # Mutation sur un individu au hasard
            index = roulette_wheel_selection(population_fitness)
            self.population[index].mutate()
        
        if random.random() < pc:
            # d est dynamique ici car sinon seul les d derniers chances
            # alors que l'on aimerai que sa soit tout les non selectionnés
            d = len(self.population) - len(selected_objects_index)
            
            # Fait le crossover autant de fois qu'il y a d'individu à détruire
            for i in range(0, d, 2):
                # Crossover sur deux individus au hasard
                dad_index = roulette_wheel_selection(population_fitness)
                mom_index = roulette_wheel_selection(population_fitness)
                childs = self.population[dad_index].crossover(self.population[mom_index])
                
                # On remplace les deux pires par les deux enfants
                index = -(i + 1)
                self.population[population_fitness[index]['index']].genotype = childs[0]
                self.population[population_fitness[index - 1]['index']].genotype = childs[1]
                
    def display(self):
        last_data = [p.data() for p in self.population]

        for i in range(3):
            for j in range(3):
                # Calcule de l'index pour last_data
                index = (i  * 3) + j
                
                # on unpack les valeur
                color, scale, extrudes = last_data[index]
                
                # Création du cube centrale de la créature
                mode_set(mode='OBJECT')
                bpy.ops.mesh.primitive_cube_add(location=((i % 3) * 5, 0, (j % 3) * 5))
                cube = bpy.context.active_object  # Permet d'accèder au cube que je viens de créer
                cube.name = f'Cube{index}'
                
                # On déselectionne tout
                mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                
                for extrude in extrudes:
                    face, location = extrude
                    print(face)
                    if face < len(cube.data.polygons):
                        # On selectionne une face à extrude
                        cube.data.polygons[face].select = True
                        # On extrude a la position
                        mode_set(mode='EDIT')
                        bpy.ops.mesh.extrude_context_move(
                            TRANSFORM_OT_translate={
                                "value": location,
                                "orient_type":'NORMAL'
                            }
                        )
                
                material = bpy.data.materials.new(name='Material')
                # On spécifie que l'on veut utiliser les node
                material.use_nodes = True
                material_nodes = material.node_tree.nodes
                material_links = material.node_tree.links
                
                # On récupère la node Principled BSDF
                diffuse = material_nodes['Principled BSDF']
                # On modifie ca valeur d'emission
                diffuse.inputs['Emission'].default_value = color
                
                # On crée une nouvelle node de type ShaderNodeTexMusgrave
                musgrave = material_nodes.new('ShaderNodeTexMusgrave')
                # On modifie sa valeur de scale
                musgrave.inputs['Scale'].default_value = scale
                
                # On fait le lien entre la sortie de la nouvelle node vers la valeur désiré, ici Fac vers Base Color
                material_links.new(musgrave.outputs['Fac'], diffuse.inputs['Base Color'])
                      
                cube.data.materials.append(material)
                
                # Affiche le genotype dans la console
                print(f'Cube n°{index} : ' + ''.join(str(x) for x in self.population[index].genotype))

        # Change le viewport shading pour pouvoir voir les shaders 
        for area in bpy.context.screen.areas: 
            if area.type == 'VIEW_3D':
                for space in area.spaces: 
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'

class People(object):
    genotype = []
    
    def __init__(self, genotype=None):
        if genotype is None:
            genotype = [random.choice([0, 1]) for i in range(40)]
        self.genotype = genotype
        
    # Tire en random un bit du génome et le change (0 <-> 1)
    def mutate(self):
        index = random.randint(0, len(self.genotype) - 1) 
        self.genotype[index] = 1 - self.genotype[index]
    
    def crossover(self, other):
        max = min(len(self.genotype) - 1, len(other.genotype) -1)
        index = random.randint(0, max)
        
        dad_beg = self.genotype[0:index]
        dad_end = self.genotype[index:]
        
        mom_beg = other.genotype[0:index]
        mom_end = other.genotype[index:]
        
        return (dad_beg + mom_end, mom_beg + dad_end)
    
    def data(self):
        color = (
            bitshifting(self.genotype[0:8]) / 255,    # Red
            bitshifting(self.genotype[8:16]) / 255,   # Green
            bitshifting(self.genotype[16:24]) / 255,  # Blue
            bitshifting(self.genotype[24:32]) / 255   # Alpha
        )
        scale = bitshifting(self.genotype[32:40])
        
        extrudes = []
        for i in range(40, len(self.genotype), (8 * 4)):
            face = bitshifting(self.genotype[i:i + 8])
            extrude_position = (
                bitshifting(self.genotype[i + (8 * 1):i + (8 * 2)]),  # width
                bitshifting(self.genotype[i + (8 * 2):i + (8 * 3)]),  # height
                bitshifting(self.genotype[i + (8 * 3):i + (8 * 4)])   # depth
            )
            extrudes.append([face, extrude_position])
        
        return (color, scale, extrudes)
                        
class Entoform(People):
    face_total = 6
    
    def __init__(self):
        super().__init__()
        for i in range(8):
            self.extrude()      
     
    def extrude(self):
        if random.random() < 0.65:
            face = to_bitlist(random.randint(0, self.face_total - 1))
            print(f"face : {face}")
            extrude_position = [random.choice([0, 1]) for i in range(24)]
            self.genotype += face 
            self.genotype += extrude_position
            
            self.face_total += 4


########################
# Main
########################

#clear_scene()
    
g = GenState()

while True:
    clear_scene()
    g.display()
    
    for i in range(2, -1, -1):
        text = ""
        for j in range(3):
            index = (i  * 3) + j
            text += f'{index} '
        print(text)
    
    # Rafraichit la vue de blender
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    
    # Attend un input de l'utilisateur dans la console
    variable = input('Select cube index : ')
    selected_objects_index = variable.split(' ')
    if variable == 'e':
        pass  # TODO : export in obj
    
    for i in range(50):
        g.evolve(selected_objects_index=selected_objects_index)