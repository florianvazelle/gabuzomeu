import bpy
import bmesh
import random
import bisect

from mathutils import Vector

########################
# Variables global
########################

bn = 8     # bit number - on va coder chaque information génétique sur bn bits

pm = 0.25  # probabilitée de mutation
pc = 0.85  # probabilitée de crossover
d  = 2     # nombre de plus mauvais que l'on détruit


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

# Raccourci pour tout déselectionner  
def deselect_all():
    mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

# Nettoye la scene en supprimant tout les mesh
def clear_scene():
    mode_set(mode = 'OBJECT')
        
    bpy.ops.object.select_by_type(type="MESH")
    bpy.ops.object.delete()
    
    bpy.ops.object.select_by_type(type="ARMATURE")
    bpy.ops.object.delete()

# Convertie un tableau de bit, en un entier en base 10
def bitshifting(bitlist: list):
    out = 0
    for bit in bitlist:
        out = (out << 1) | bit
    return out

# Convertie un entier en un tableau de bit
def to_bitlist(number: int):
    out = []
    bits = "{0:b}".format(number)
    # Si trop de bits
    if len(bits) > bn:
        # On prend seulement les bn dernier bit
        bits = bits[len(bits) - 8:]
    # Si pas assez de bits
    for i in range(8 - len(bits)):
        # On ajoute des zéro
        out.append(0)
    for bit in bits:
        out.append(int(bit))
    return out

# https://en.wikipedia.org/wiki/Fitness_proportionate_selection
def roulette_wheel_selection(choices: list):
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

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GenState:
    
    def __init__(self):
        self.population = [Entoform() for i in range(9)]
        self.generation = 0  # numéro de la génération
        
    def evolve(self, selected_objects_index=[]):
        self.generation += 1
        
        # Interactive Selection
        # selected_objects_index = [int(obj.name.replace("Cube","")) for obj in bpy.context.selected_objects]
        
        # Construction du tableau de fitness
        population_fitness = [{'fitness': 1 if i in selected_objects_index else 0, 'index': i} for i in range(len(self.population))]
        # On calcul la somme des fitness
        sum_fitness = sum(pop_fit['fitness'] for pop_fit in population_fitness)
        assert (not sum_fitness == 0)
        
        # On normalise les valeur (entre 0 et 1)
        for i in range(len(population_fitness)):
            population_fitness[i]['fitness'] = float(population_fitness[i]['fitness']) / sum_fitness
        # Et on le tri
        population_fitness = sorted(population_fitness, key=lambda x : x['fitness'], reverse=True)
        
        if random.random() < pm:
            # Mutation sur un individu au hasard
            index = roulette_wheel_selection(population_fitness)
            self.population[index].mutate()
            print(f'{bcolors.OKBLUE}mutate : n°{index}{bcolors.ENDC}')
        
        if random.random() < pc:
            # d est dynamique ici car sinon seul les d derniers seront remplacé
            # alors que l'on aimerai que sa soit tout les non selectionnés
            d = len(self.population) - len(selected_objects_index)

            # Fait le crossover autant de fois qu'il y a d'individu à détruire
            for i in range(0, d, 2):
                # Crossover sur deux individus au hasard
                dad_index = roulette_wheel_selection(population_fitness)
                mom_index = roulette_wheel_selection(population_fitness)
                childs = self.population[dad_index].crossover(self.population[mom_index])
                print(f'{bcolors.OKBLUE}crossover : dad n°{dad_index} - mom n°{mom_index}{bcolors.ENDC}')
                
                # On remplace les deux pires par les deux enfants
                index = -(i + 1)
                self.population[population_fitness[index]['index']].genotype = childs[0]
                self.population[population_fitness[index - 1]['index']].genotype = childs[1]

    
    # Applique une action sur l'ensemble de la population
    def apply(self, action: str):
        for i in range(3):
            for j in range(3):
                # Calcule de l'index
                index = (i  * 3) + j
                    
                action_op = getattr(self.population[index], action, None)
                if callable(action_op):
                    action_op(index, location=((i % 3) * 20, 0, (j % 3) * 20))

class People:
    
    # m = nombre de paramètre
    def __init__(self, m: int):
        self.genotype = [random.choice([0, 1]) for i in range(bn * m)]
        
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
    
    # Retourne les données du génotype
    # ici comportement par défaut, besoin de surchager la methode
    def data(self):
        out = []
        for i in range(0, len(self.genotype), bn):
            out.append(self.genotype[i:i + bn])
        return out
                        
class Entoform(People):
    
    def __init__(self):
        # Initalisation du génotype avec couleur (4 = rgba) et scale (1)
        super().__init__(5)
        
        # Ajoute des données d'extrude
        self.face_total = 6
        self.bones = []
        for i in range(8):
            self.extrude()  # TODO : créer les jambes ici  
        self.intervals = [l for l in range(6, self.face_total + 1, 4)]
            
    # Extrude coté génotype
    def extrude(self):
        if random.random() < 0.65:
            face = to_bitlist(random.randint(0, self.face_total - 1))

            width = to_bitlist(random.randint(0, 4))
            height = to_bitlist(random.randint(0, 4))
            depth = to_bitlist(random.randint(0, 4))
            
            self.genotype += face 
            self.genotype += width + height + depth
            
            self.face_total += 4
    
    # Petite surchage du crossover normal
    def crossover(self, other):
        # On va orienter l'index de découpe que l'on selectionne
        # Ainsi il va tomber sur un parametètre et les enfants seront un peu plus cohérent 
        max = min(len(self.genotype), len(other.genotype))
        index = random.choice([i for i in range(0, max, bn)])
        
        dad_beg = self.genotype[0:index]
        dad_end = self.genotype[index:]
        
        mom_beg = other.genotype[0:index]
        mom_end = other.genotype[index:]
        
        return (dad_beg + mom_end, mom_beg + dad_end)
            
    # Retourne les données 'formaté' du génotype
    def data(self):
        color = (
            bitshifting(self.genotype[0:bn]) / 255,           # Red
            bitshifting(self.genotype[bn:bn * 2]) / 255,      # Green
            bitshifting(self.genotype[bn * 2:bn * 3]) / 255,  # Blue
            bitshifting(self.genotype[bn * 3:bn * 4]) / 255   # Alpha
        )
        scale = bitshifting(self.genotype[bn * 4:bn * 5]) / 20
        
        extrudes = []
        for i in range(bn * 5, len(self.genotype), (bn * 4)):
            face = bitshifting(self.genotype[i:i + bn])
            extrude_position = (
                bitshifting(self.genotype[i + (bn * 1):i + (bn * 2)]),  # width
                bitshifting(self.genotype[i + (bn * 2):i + (bn * 3)]),  # height
                bitshifting(self.genotype[i + (bn * 3):i + (bn * 4)])   # depth
            )
            extrudes.append([face, extrude_position])
        
        return (color, scale, extrudes)    
    
    # Rig l'entoform coté blender 
    # TODO : remove index param       
    def rigging(self, index: int, location=(0, 0, 0)):
        if len(self.bones) > 0:
                
            # création de l'armature
            mode_set(mode='OBJECT')
            bpy.ops.object.armature_add(location=location)
            armature = bpy.context.active_object
            armature.name = f'Armature{index}'

            mode_set(mode='EDIT')
            all_bones = [bpy.context.active_bone]
            
            for b in self.bones:
                # On unpack les valeurs
                index_parent_bone, head, tail = b.values()
                assert len(self.bones) > index_parent_bone
                
                # On crée l'armature
                bone = armature.data.edit_bones.new(name=f'Bone{index}')
                # On lui assigne ses postions correspondante 
                bone.head = head
                bone.tail = tail
                
                if not index_parent_bone == 0:
                    bone.use_connect = True
                bone.use_relative_parent = True
                bone.parent = all_bones[index_parent_bone]
                
                all_bones.append(bone)
            
            mode_set(mode='OBJECT')
            cube = bpy.data.objects[f'Cube{index}']
            cube.select_set(True)
            armature.select_set(True)
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    # Affiche l'entoform coté blender
    def display(self, index: int, location=(0, 0, 0)):
        self.bones = []  # On réinitialise les info des bones
        
        # on unpack les valeur
        color, scale, extrudes = self.data()
        
        # Création du cube centrale de la créature
        mode_set(mode='OBJECT')
        bpy.ops.mesh.primitive_cube_add(location=location)
        cube = bpy.context.active_object  # Permet d'accèder au cube que je viens de créer
        cube.name = f'Cube{index}'

        # On déselectionne tout
        deselect_all()
        
        for extrude in extrudes:
            face, location = extrude
            if face < len(cube.data.polygons):
                # On selectionne une face à extrude
                mode_set(mode='OBJECT')
                cube.data.polygons[face].select = True
                # On extrude a la position
                mode_set(mode='EDIT')
                bpy.ops.mesh.extrude_context_move(
                    TRANSFORM_OT_translate={
                        "value": location,
                        "orient_type":'NORMAL'
                    }
                )               
                
                # On stock les positions clés de l'extrude
                # TODO : ne pas faire ca ici
                mode_set(mode='EDIT')
                
                b_cube = bmesh.from_edit_mesh(cube.data)            
                selected_face = [b_face for b_face in b_cube.faces if b_face.select == True]        
                assert len(selected_face) == 1
                
                selected_face = selected_face[0]
                
                head = selected_face.calc_center_bounds()
                tail = head + selected_face.normal
                
                # 0 <= et < 6   -> parent_bone = main_bone
                # 6 <= et < 10  -> parent_bone = bone premiere extrude
                # 10 <= et < 14 -> parent_bone = bone deuxieme extrude ...
                
                index_parent_bone = bisect.bisect_right(self.intervals, face) 
                self.bones.append({
                    'index_parent_bone': index_parent_bone,
                    'head': head,
                    'tail': tail
                })
                
                # Déselectionne tout pour avoir seulement une face selectionné
                deselect_all()
                        
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


########################
# Main
########################

selected_objects_index = []

# Change le viewport shading pour pouvoir voir les shaders 
for area in bpy.context.screen.areas: 
    if area.type == 'VIEW_3D':
        for space in area.spaces: 
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
    
g = GenState()

while True:
    clear_scene()
    
    g.apply('display')
    
    for i in range(2, -1, -1):
        text = ""
        for j in range(3):
            index = i + (j  * 3)
            text += f'{index} '
        print(text)
    
    # Rafraichit la vue de blender
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    
    while True:
        # Attend un input de l'utilisateur dans la console
        inputs = input('Select cube index (help h): ')
        
        # Quick interpreter
        if inputs == 'h': print('h - help\nq - quit\nr - rig\ne - export')
        elif inputs == 'r': g.apply('rigging'); bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        elif inputs == 'e': bpy.ops.export_scene.fbx(filepath="./test.fbx")    
        else: variable = inputs; break
    if variable == 'q': break
    
    # Si rien, on garde les parents précédent
    if not len(variable) == 0:
        selected_objects_index = [int(v) for v in variable.split(' ') if v in [str(i) for i in range(9)]]
    
    # Seulement si, aucun input n'a été saisi et qu'il s'agit de la première génération
    if len(selected_objects_index) == 0:
        # On regénére toute les individus
        g = GenState()
    else:
        g.evolve(selected_objects_index=selected_objects_index)