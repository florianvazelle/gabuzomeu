using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class AddRagdoll : MonoBehaviour
{
    private Transform root;

    void Start()
    {
        Transform[] allchildren = this.transform.GetComponentsInChildren<Transform>();
        for (int i = 1; i < allchildren.Length; i++)
        {
            if (allchildren[i].name.Contains("Armature")) {
                root = allchildren[i].GetChild(0);
                break;
            }
        }

        root.gameObject.AddComponent<Rigidbody>();
        var sphere = root.gameObject.AddComponent<SphereCollider>();
        sphere.radius = 0.01f;

        foreach (Transform child in root)
        {
            var AllRigidbody = new List<Rigidbody>();

            Transform tmp = child;
            while (!tmp.name.Contains("end"))
            {
                int i = AllRigidbody.Count;

                CharacterJoint joint = tmp.gameObject.AddComponent<CharacterJoint>();
                joint.connectedBody = (i == 0) ? root.GetComponent<Rigidbody>() : AllRigidbody[i - 1];

                CapsuleCollider collider = tmp.gameObject.AddComponent<CapsuleCollider>();
                collider.center = new Vector3(0.0f, 0.005f, 0.0f);
                collider.radius = 0.001f;
                collider.height = 0.005f;

                AllRigidbody.Add(tmp.gameObject.GetComponent<Rigidbody>());

                tmp = tmp.GetChild(0);
            }
        };
    }
}
