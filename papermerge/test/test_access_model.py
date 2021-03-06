from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from papermerge.core.auth import create_access, set_access_perms
from papermerge.core.models import Access, Diff, Folder
from papermerge.test.utils import create_margaret_user, create_uploader_user

READ = Access.PERM_READ
WRITE = Access.PERM_WRITE
DELETE = Access.PERM_DELETE

FULL_ACCESS = [
    Access.PERM_READ,
    Access.PERM_WRITE,
    Access.PERM_DELETE,
    Access.PERM_CHANGE_PERM,
    Access.PERM_TAKE_OWNERSHIP,
]


class TestAccessDiff(TestCase):
    def setUp(self):
        self.margaret_user = create_margaret_user()
        self.uploader_user = create_uploader_user()
        self.R = Permission.objects.get(codename=READ)
        self.W = Permission.objects.get(codename=WRITE)
        self.D = Permission.objects.get(codename=DELETE)

    def test_set_access_perms_returns_correct_diffs_1(self):
        """
        Here we are concerned only with returned value of set_access_perms.
        Let's test the simplest case.
        1. Given New folder created by uploader
        2. User tries to set one access entry for margaret
        """
        node = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        access_diffs = set_access_perms(
            node,
            [
                {
                    'model': 'user',
                    'name': 'margaret',
                    'access_type': 'allow',
                    'permissions': {
                        'read': True,
                        'write': True,
                        'delete': True
                    }
                }
            ]
        )

        # only one entry AccessDiff(operation=ADD)
        self.assertEqual(
            len(access_diffs),
            1,
            [str(diff) for diff in access_diffs]
        )

        self.assertEqual(
            access_diffs[0].operation,
            Diff.ADD
        )

        access = access_diffs[0].pop()
        self.assertEqual(
            "margaret", access.user.username
        )
        self.assertEqual(
            "allow", access.access_type
        )
        perms = set()
        perms.add("read")
        perms.add("write")
        perms.add("delete")

        self.assertEqual(
            perms,
            access.perms_codenames()
        )

    def test_set_access_perms_returns_correct_diffs_2(self):
        """
        1. New folder is created by uploader
        2. New folder has margaret READ & WRITE & DELETE access (allow)
        3. User tries to leave for margaret only read permission.
         (it will set_access_perms only with READ flag)
        """
        node = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )

        create_access(
            node=node,
            model_type=Access.MODEL_USER,
            name=self.margaret_user,
            access_type=Access.ALLOW,
            access_inherited=False,
            permissions={
                READ: True,
                WRITE: True,
                DELETE: True
            }
        )
        access_diffs = set_access_perms(
            node,
            [
                {
                    'model': 'user',
                    'name': 'margaret',
                    'access_type': 'allow',
                    'permissions': {
                        'read': True,  # only read flag
                    }
                }
            ]
        )
        # only one entry AccessDiff(operation=ADD)
        self.assertEqual(
            len(access_diffs),
            1,
            [str(diff) for diff in access_diffs]
        )

        self.assertEqual(
            access_diffs[0].operation,
            Diff.UPDATE
        )

        access = access_diffs[0].pop()
        self.assertEqual(
            "margaret", access.user.username
        )
        self.assertEqual(
            "allow", access.access_type
        )
        perms = set()
        perms.add("read")

        self.assertEqual(
            perms,
            access.perms_codenames()
        )


class TestAccessModelEquality(TestCase):
    def setUp(self):
        self.margaret_user = create_margaret_user()
        self.uploader_user = create_uploader_user()
        self.R = Permission.objects.get(codename=READ)
        self.W = Permission.objects.get(codename=WRITE)
        self.D = Permission.objects.get(codename=DELETE)

    def test_access_equality_op1(self):
        """
        test basic access model equality operation
        (same user)
        """

        some_folder = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        a1 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            user=self.uploader_user
        )
        a2 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            user=self.uploader_user
        )
        a1.save()
        a2.save()
        self.assertEqual(a1, a2)

        a1.permissions.add(self.R)
        a2.permissions.add(self.W)

        self.assertEqual(a1, a2)

    def test_access_equality_op2(self):
        """
        User attribute differs => access models won't be equal.
        """

        some_folder = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        a1 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            user=self.margaret_user
        )
        a2 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            user=self.uploader_user
        )
        a1.save()
        a2.save()
        # user attribute differs (margaret vs uploader)
        self.assertNotEqual(a1, a2)

        a1.permissions.add(self.R)
        a2.permissions.add(self.W)

        # permissions does not metter, users differ
        self.assertNotEqual(a1, a2)

    def test_access_equality_op3(self):
        """
        Group attribute differs => access models won't be equal.
        """
        g1 = Group(name="G1")
        g1.save()
        g2 = Group(name="G2")
        g2.save()
        some_folder = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        a1 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            group=g1
        )
        a2 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            group=g2
        )
        a1.save()
        a2.save()
        # group attribute differ
        self.assertNotEqual(a1, a2)

    def test_access_equality_op4(self):
        """
        match by group
        """
        g = Group(name="G")
        g.save()
        some_folder = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        a1 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            group=g
        )
        a2 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            group=g
        )
        a1.save()
        a2.save()
        # group attribute differ
        self.assertEqual(a1, a2)

    def test_access_equality_op_inheritance(self):
        """
        Inheritance flag does not matter.
        """
        some_folder = Folder.objects.create(
            title="some_folder",
            user=self.uploader_user
        )
        a1 = Access(
            access_type=Access.ALLOW,
            access_inherited=False,
            node=some_folder,
            user=self.margaret_user
        )
        a2 = Access(
            access_type=Access.ALLOW,
            access_inherited=True,  # different, but it does not matter
            node=some_folder,
            user=self.margaret_user
        )
        a1.save()
        a2.save()
        # inheritance flag does not matter on eq op.
        self.assertEqual(a1, a2)


class TestAccessModel(TestCase):

    def setUp(self):
        self.margaret_user = create_margaret_user()
        self.uploader_user = create_uploader_user()
        self.R = Permission.objects.get(codename=READ)
        self.W = Permission.objects.get(codename=WRITE)
        self.D = Permission.objects.get(codename=DELETE)

    def test_newly_created_folder_owner_full_right(self):
        """
        The owner of the newly created folder has full
        access permissions.
        """
        new_folder = Folder.objects.create(
            title="creator_owns_me",
            user=self.uploader_user
        )
        self.assertTrue(
            self.uploader_user.has_perms(FULL_ACCESS, new_folder)
        )

    def test_newly_created_subfolder_inherits_from_parent(self):
        """
        Newly created folder inherits access permissions from its
        parent folder.
        """
        new_folder = Folder.objects.create(
            title="creator_owns_me",
            user=self.uploader_user
        )
        # create custom read access for margaret
        create_access(
            node=new_folder,
            model_type=Access.MODEL_USER,
            name=self.margaret_user,
            access_type=Access.ALLOW,
            access_inherited=False,
            permissions={
                READ: True
            }  # allow read access to margaret
        )

        sub_folder = Folder.objects.create(
            title="subfolder for margaret",
            user=self.uploader_user,
            parent=new_folder
        )

        # and subfolder inherited access permissions from its parent
        self.assertTrue(
            self.uploader_user.has_perms(FULL_ACCESS, sub_folder)
        )

        # margaret can read it (because parent folder is readable by parent)
        self.assertTrue(
            self.margaret_user.has_perm(READ, sub_folder)
        )

        # but margaret cannot write to it, because so are
        # access permissions inherited from parent folder.
        self.assertFalse(
            self.margaret_user.has_perm(WRITE, sub_folder)
        )
        self.assertFalse(
            self.margaret_user.has_perms(FULL_ACCESS, sub_folder)
        )

    def test_changes_resursive_inheritance(self):
        """
        1. uploader creates:
            F1 -> L1a -> L2a -> L3a
            F1 -> L1b -> L2b

        2. Uploader gives read access to margaret on F1

        3. Margaret will have read access on L1a, L1b, L2a, L2b,
            L3a as well (because of recursive inheritance)
        """
        F1 = Folder.objects.create(
            title="F1",
            user=self.uploader_user
        )
        L1a = Folder.objects.create(
            title="L1a",
            user=self.uploader_user,
            parent=F1
        )
        L2a = Folder.objects.create(
            title="L2a",
            user=self.uploader_user,
            parent=L1a
        )
        L3a = Folder.objects.create(
            title="L3a",
            user=self.uploader_user,
            parent=L2a
        )
        L1b = Folder.objects.create(
            title="L1b",
            user=self.uploader_user,
            parent=F1
        )
        L2b = Folder.objects.create(
            title="L2b",
            user=self.uploader_user,
            parent=L1b
        )
        # give margaret read access on topmost folder
        new_access = create_access(
            node=F1,
            model_type=Access.MODEL_USER,
            name=self.margaret_user,
            access_type=Access.ALLOW,
            access_inherited=False,
            permissions={
                READ: True
            }  # allow read access to margaret
        )
        # function which does the trick
        access_diff = Diff(
            operation=Diff.ADD,
            instances_set=[new_access]

        )
        F1.propagate_changes(
            diffs_set=[access_diff],
            apply_to_self=True
        )

        # and assert
        for folder in [F1, L1a, L1b, L2a, L3a, L2b]:
            self.assertTrue(
                self.margaret_user.has_perm(READ, folder),
                f"margaret: Failed for folder {folder.title}"
            )
            # uploader still has full access ?
            self.assertTrue(
                self.uploader_user.has_perms(FULL_ACCESS, folder),
                f"uploader: Failed for folder {folder.title}"
            )

    def test_move_files_from_uploader_to_margaret(self):
        """
        Uploader creates following folder struture:

        1.
            * upload/for_margaret/mx1
            * upload/for_margaret/mx2

        2.
        uploader Creates root level folder shared_documents
        and assigns it full access to margaret:

            * upload/for_margaret/mx1
            * upload/for_margaret/mx2
            * shared_folder  <- both uploader and margaret have full access

        3. uploader moves folder for_margaret into shared_folder:

            * upload
            * shared_folder/for_margaret/mx1
            * shared_folder/for_margaret/mx1

        4. Margaret can now see and access all for_margaret, mx1 and mx2:

            * shared_folder/for_margaret/mx1
            * shared_folder/for_margaret/mx1

        5. Margaret creates private folder margaret_private

        6. Margaret moves shared_folder/for_margaret into margaret_private:

            * shared_folder
            * margaret_private/for_margaret/mx1
            * margaret_private/for_margaret/mx2

        7. Now ONLY margaret can see and access
            * margaret_private/for_margaret/
            * margaret_private/for_margaret/mx1
            * margaret_private/for_margaret/mx2

        Why?
        Because moved folders for_margaret, mx1, mx2 inherited
        their new access rights from their new parent while
        old access rights were deleted.
        """
        # 1
        upload = Folder.objects.create(
            title="upload",
            user=self.uploader_user
        )
        for_margaret = Folder.objects.create(
            title="for_margaret",
            user=self.uploader_user,
            parent=upload
        )
        mx1 = Folder.objects.create(
            title="mx1",
            user=self.uploader_user,
            parent=for_margaret
        )
        mx2 = Folder.objects.create(
            title="mx2",
            user=self.uploader_user,
            parent=for_margaret
        )
        # 2
        shared_folder = Folder.objects.create(
            title="shared_folder",
            user=self.uploader_user
        )
        create_access(
            node=shared_folder,
            model_type=Access.MODEL_USER,
            name=self.margaret_user,
            access_inherited=False,
            access_type=Access.ALLOW,
            permissions={
                Access.PERM_READ: True,
                Access.PERM_WRITE: True,
                Access.PERM_DELETE: True,
                Access.PERM_TAKE_OWNERSHIP: True,
                Access.PERM_CHANGE_PERM: True
            }
        )

        self.assertTrue(
            self.margaret_user.has_perms(FULL_ACCESS, shared_folder)
        )
        self.assertTrue(
            self.uploader_user.has_perms(FULL_ACCESS, shared_folder)
        )

        # as of yet, margaret does not has access to mx1, mx2, for_margaret
        for folder in [mx1, mx2, for_margaret]:
            self.assertFalse(
                self.margaret_user.has_perms(FULL_ACCESS, folder),
                f"Failed for folder {folder.title}"
            )

        # 3 - uploader moves folder for_margaret into shared_folder

        Folder.objects.move_node(for_margaret, shared_folder)
        # 4 - margaret now has full access to for_margaret, mx1, mx2
        for folder in [mx1, mx2, for_margaret]:
            # both, margaret and upload have full access
            self.assertTrue(
                self.margaret_user.has_perms(FULL_ACCESS, folder),
                f"Failed for folder {folder.title}"
            )
            self.assertTrue(
                self.uploader_user.has_perms(FULL_ACCESS, folder),
                f"Uploader has access to {folder.title}. Wrong code!"
            )

        # 5. Margaret creates private folder margaret_private
        private_folder = Folder.objects.create(
            title="private",
            user=self.margaret_user
        )

        # 6. Margaret moves shared_folder/for_margaret into margaret_private:
        Folder.objects.move_node(
            for_margaret,   # node to move
            private_folder  # new parent
        )

        # 7
        for folder in [mx1, mx2, for_margaret]:
            self.assertTrue(
                self.margaret_user.has_perms(FULL_ACCESS, folder),
                f"Failed for folder {folder.title}"
            )
            # uploader lost its access permissions for mx1, mx2,
            # for_margaret folders
            self.assertFalse(
                self.uploader_user.has_perms(FULL_ACCESS, folder),
                f"Failed for folder {folder.title}"
            )
