# filters.py (Funciones de filtrado de usuarios)
from database.models import collection_seguidos  # Si necesitas acceder a usuarios seguidos


def aplicar_filtros(user, filtros):
    # Filtrar por ubicación
    if not any(ubicacion in user.biography.lower() for ubicacion in filtros["ubicaciones"]):
        return False

    # Filtrar por palabras clave en la biografía
    if not any(palabra in user.biography.lower() for palabra in filtros["palabras_clave"]):
        return False

    # Filtrar por cantidad mínima de publicaciones y seguidores
    if user.media_count < filtros["min_publicaciones"] or user.follower_count < filtros["min_seguidores"]:
        return False

    # Filtrar por tipo de cuenta
    if (filtros["tipo_cuenta"] == "publica" and user.is_private) or (filtros["tipo_cuenta"] == "privada" and not user.is_private):
        return False

    return True

def filtrar_usuarios(usuarios, filtros):
    print(f"Aplicando filtros a {len(usuarios)} usuarios...")
    usuarios_filtrados = []
    usuarios_omitidos = []

    for usuario in usuarios:
        motivo_exclusion = None  # Variable para almacenar el motivo de exclusión
        try:
            # Filtro por ubicación
            if filtros["ubicaciones"] and not any(
                ubicacion.lower() in (usuario.biography or "").lower() for ubicacion in filtros["ubicaciones"]
            ):
                motivo_exclusion = "ubicación no coincide"
            
            # Filtro por palabras clave
            elif filtros["palabras_clave"] and not any(
                palabra.lower() in (usuario.biography or "").lower() for palabra in filtros["palabras_clave"]
            ):
                motivo_exclusion = "sin palabras clave en biografía"

            # Filtro por publicaciones y seguidores
            elif usuario.media_count < filtros["min_publicaciones"]:
                motivo_exclusion = f"menos de {filtros['min_publicaciones']} publicaciones ({usuario.media_count})"
            
            elif usuario.follower_count < filtros["min_seguidores"]:
                motivo_exclusion = f"menos de {filtros['min_seguidores']} seguidores ({usuario.follower_count})"
            
            # Filtro por tipo de cuenta
            elif filtros["tipo_cuenta"] == "publica" and usuario.is_private:
                motivo_exclusion = "cuenta privada"

            # Si no hay motivo de exclusión, añadir a filtrados
            if motivo_exclusion is None:
                usuarios_filtrados.append(usuario)
            else:
                usuarios_omitidos.append((usuario.username, motivo_exclusion))

        except Exception as e:
            print(f"Error al filtrar usuario @{usuario.username}: {e}")
            usuarios_omitidos.append((usuario.username, "error en filtro"))

    return usuarios_filtrados, usuarios_omitidos
